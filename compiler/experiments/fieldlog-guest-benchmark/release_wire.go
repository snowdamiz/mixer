// Re-emit draft-validation bodies with the stock Go v3 wire types.
package main

import (
	"encoding/json"
	"fmt"
	"os"

	"mixer/services/protocol"
)

type artifact struct {
	SignedManifest protocol.SignedManifestV3 `json:"signed_manifest"`
	Payload        []byte                    `json:"payload"`
}

type material struct {
	SignedAssignment protocol.SignedAssignmentV3 `json:"signed_assignment"`
	ArtifactURL      string                      `json:"artifact_url"`
	Artifact         artifact                    `json:"artifact"`
}

type bodies struct {
	Offer    []byte `json:"offer"`
	Artifact []byte `json:"artifact"`
}

func encode() error {
	if len(os.Args) != 2 {
		return fmt.Errorf("usage: release_wire INPUT_JSON")
	}
	input, err := os.Open(os.Args[1])
	if err != nil {
		return err
	}
	defer input.Close()
	var samples []material
	if err := json.NewDecoder(input).Decode(&samples); err != nil {
		return err
	}
	result := make([]bodies, 0, len(samples))
	for _, sample := range samples {
		offer, err := json.Marshal(map[string]any{
			"signed_assignment": sample.SignedAssignment,
			"artifact_url":      sample.ArtifactURL,
		})
		if err != nil {
			return err
		}
		body, err := json.Marshal(sample.Artifact)
		if err != nil {
			return err
		}
		result = append(result, bodies{Offer: offer, Artifact: body})
	}
	return json.NewEncoder(os.Stdout).Encode(result)
}

func main() {
	if err := encode(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
