// Host-only independent execution of the existing owned Go wire authority.
package main

import (
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "os"
 "mixer/services/protocol"
)

type signedCase struct { Name string `json:"name"`; Accepted bool `json:"accepted"`; JSON string `json:"signed_manifest_json"` }
type textCase struct { Value string `json:"value"`; Accepted bool `json:"accepted"` }
type result struct { Kind string `json:"kind"`; Name string `json:"name"`; InputSHA string `json:"inputSHA256"`; Expected bool `json:"expected"`; Accepted bool `json:"accepted"` }
func hash(b []byte) string { s:=sha256.Sum256(b);return hex.EncodeToString(s[:]) }
func main() {
 fbytes,e:=os.ReadFile(os.Args[1]);if e!=nil {panic(e)}
 var f struct { Signed json.RawMessage `json:"signed_manifest"`; Payload []byte `json:"payload"`; Roots []protocol.Root `json:"roots"`; Host protocol.Host `json:"host"`; Now uint64 `json:"verification_time_unix"` }
 if e=json.Unmarshal(fbytes,&f); e!=nil {panic(e)}
 cbytes,e:=os.ReadFile(os.Args[2]);if e!=nil {panic(e)}
 var c struct { Cases []signedCase `json:"cases"`; Origins []textCase `json:"origin_cases"`; Namespaces []textCase `json:"namespace_cases"`; Assignments []json.RawMessage `json:"assignment_cases"` }
 if e=json.Unmarshal(cbytes,&c);e!=nil {panic(e)}
 if len(c.Cases)!=154 || len(c.Origins)!=39 || len(c.Namespaces)!=14 ||len(c.Assignments)!=36 {panic("counts")}
 results:=[]result{}
 verify:=func(b []byte) bool {s,e:=protocol.DecodeSignedManifestV3(b);if e==nil {e=protocol.VerifyManifestV3(s,f.Payload,f.Roots,f.Host,f.Now)};return e==nil}
 results=append(results,result{"fixture","signed_manifest",hash(f.Signed),true,verify(f.Signed)})
 for _,v:=range c.Cases {results=append(results,result{"manifest",v.Name,hash([]byte(v.JSON)),v.Accepted,verify([]byte(v.JSON))})}
 for _,v:=range c.Origins {results=append(results,result{"origin",v.Value,hash([]byte(v.Value)),v.Accepted,protocol.ValidGrantOrigin(v.Value)})}
 for _,v:=range c.Namespaces {
  g:=protocol.CapabilityGrants{Schema:1,SchemaSHA256:protocol.GrantSchemaSHA256,Entries:[]protocol.CapabilityGrant{{CapabilityID:protocol.StorageGrantID,SchemaSHA256:protocol.StorageGrantSHA256,Permissions:[]string{},Origins:[]string{},Methods:[]string{},Namespaces:[]string{v.Value}}}}
  e:=g.Validate(map[string]string{protocol.StorageGrantID:protocol.StorageGrantSHA256})
  results=append(results,result{"namespace",v.Value,hash([]byte(v.Value)),v.Accepted,e==nil})
 }
 for _,r:=range results {if r.Expected!=r.Accepted {panic("parity: "+r.Kind+"/"+r.Name)}}
 data,e:=json.MarshalIndent(map[string]any{"results":results,"assignmentCasesOutOfScope":36,"fixtureFileSHA256":hash(fbytes),"corpusFileSHA256":hash(cbytes)},"","  ");if e!=nil {panic(e)}
 if e=os.WriteFile(os.Args[3],append(data,'\n'),0600);e!=nil {panic(e)}
}
