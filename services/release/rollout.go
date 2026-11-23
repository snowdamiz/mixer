package release

import (
	"encoding/json"
	"net/http"

	"mixer/services/protocol"
)

// ChannelChange describes the signed channel heads on either side of a v3 mutation.
type ChannelChange struct {
	Scope    protocol.Scope `json:"scope"`
	Runtime  string         `json:"runtime"`
	Channel  string         `json:"channel"`
	Previous *ChannelHead   `json:"previous,omitempty"`
	Current  ChannelHead    `json:"current"`
}

type ChannelHead struct {
	Sequence           uint64 `json:"sequence"`
	ArtifactSHA256     string `json:"artifact_sha256"`
	RolloutBasisPoints uint64 `json:"rollout_basis_points"`
}

func channelHead(a protocol.Assignment) ChannelHead {
	return ChannelHead{Sequence: a.Sequence, ArtifactSHA256: a.ArtifactSHA256, RolloutBasisPoints: a.RolloutBasisPoints}
}

func describeChannelChange(old Channel, exists bool, a protocol.Assignment) *ChannelChange {
	change := &ChannelChange{Scope: a.Scope, Runtime: a.Runtime, Channel: a.Channel, Current: channelHead(a)}
	if exists {
		previous := channelHead(old.assignment())
		change.Previous = &previous
	}
	return change
}

// RolloutHealth records an operator's observed installation outcomes for one
// assignment. The counts describe the observed sample, not the fleet.
type RolloutHealth struct {
	Sequence       uint64 `json:"sequence"`
	Activated      uint64 `json:"activated"`
	Pending        uint64 `json:"pending"`
	AdverseSignals uint64 `json:"adverse_signals"`
}

type RolloutHalt struct {
	Scope          protocol.Scope `json:"scope"`
	Runtime        string         `json:"runtime"`
	Channel        string         `json:"channel"`
	ArtifactSHA256 string         `json:"artifact_sha256"`
	HaltSequence   uint64         `json:"halt_sequence"`
	Health         RolloutHealth  `json:"health"`
}

func (s *Server) haltRollout(r *http.Request, channel string, who access, key string, event Event) (Response, error) {
	var req struct {
		Signed protocol.SignedAssignmentV3 `json:"signed_assignment"`
		Health json.RawMessage             `json:"health"`
	}
	raw, e := bodyV3(r, &req, maxV3MutationBody, "signed_assignment", "health")
	if e != nil {
		return Response{}, e
	}
	var health RolloutHealth
	if _, e = closedStorageObject(req.Health, "sequence", "activated", "pending", "adverse_signals"); e != nil {
		return Response{}, apiError{400, "invalid_json", e.Error()}
	}
	if e = protocol.DecodeJSON(req.Health, &health); e != nil {
		return Response{}, apiError{400, "invalid_json", e.Error()}
	}
	if health.Sequence == 0 || health.AdverseSignals == 0 {
		return Response{}, apiError{422, "invalid_health", "halt requires an adverse health signal for the rollout sequence"}
	}
	signed := Channel{Version3: &req.Signed}
	a := signed.assignment()
	if !who.matches(a.Scope) {
		return Response{}, apiError{403, "scope_denied", "signed assignment tenant differs from route"}
	}
	if a.Channel != channel || a.RolloutBasisPoints != 0 {
		return Response{}, apiError{422, "invalid_halt", "halt requires a signed zero-percent assignment for this channel"}
	}
	if e := s.requireFeatureUIArtifact(r.Context(), who, a.ArtifactSHA256, 3); e != nil {
		return Response{}, e
	}
	host, e := s.host(a.Scope, a.Runtime)
	if e != nil {
		return Response{}, e
	}
	if host.Protocol != 3 {
		return Response{}, apiError{422, "protocol_mismatch", "halt requires a registered v3 host"}
	}
	event.RolloutHalt = &RolloutHalt{
		Scope: a.Scope, Runtime: a.Runtime, Channel: channel, ArtifactSHA256: a.ArtifactSHA256,
		HaltSequence: a.Sequence, Health: health,
	}
	hash := protocol.Hash(append([]byte(r.Method+" "+r.URL.Path+"\x00"), raw...))
	return s.db.transaction(r.Context(), who, "publisher", key, hash, event, func(db releaseTransaction) (Response, error) {
		ck := channelKey(a)
		current, ok, e := db.channel(ck)
		if e != nil {
			return Response{}, e
		}
		prior := current.assignment()
		if !ok || current.version() != 3 || prior.Sequence != health.Sequence ||
			prior.RolloutBasisPoints == 0 || prior.ArtifactSHA256 != a.ArtifactSHA256 {
			return Response{}, apiError{409, "stale_rollout", "health must describe the active rollout being halted"}
		}
		rec, ok, e := db.artifact(a.ArtifactSHA256)
		if e != nil {
			return Response{}, e
		}
		if !ok || !rec.Published || rec.version() != 3 {
			return Response{}, apiError{409, "stale_rollout", "current rollout artifact is unavailable"}
		}
		// The halt removes eligibility. An expired artifact must not prevent a
		// current assignment signer from stopping offers for that artifact.
		now := uint64(s.now().Unix())
		var signatureErr error
		if host.featureUI != nil {
			signatureErr = host.featureUI.VerifyHalt(req.Signed, rec.Version3.SignedManifest.Manifest, channel, prior.Sequence, now)
		} else {
			signatureErr = protocol.VerifyAssignmentSignatureV3(req.Signed, s.cfg.Roots, now)
		}
		if a.Sequence <= prior.Sequence || signatureErr != nil {
			return Response{}, apiError{409, "assignment_rejected", "halt requires a current signature and a higher sequence"}
		}
		if e := db.saveChannel(ck, signed); e != nil {
			return Response{}, e
		}
		return response(200, event.RolloutHalt), nil
	})
}
