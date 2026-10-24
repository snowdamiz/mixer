// Independent preservation check, invoking existing exported Go Event and protocol.Hash.
package main
import("encoding/json";"fmt";"os";"mixer/services/release";"mixer/services/protocol")
func main(){
 expectedRaw,err:=os.ReadFile(os.Args[1]);if err!=nil{panic(err)}
 var expected struct{Preimage string `json:"preimage"`;Hash string `json:"hash"`;Final string `json:"final"`};if err=json.Unmarshal(expectedRaw,&expected);err!=nil{panic(err)}
 event:=release.Event{ID:1,Organization:"o",Project:"p",Actor:"legacy-actor",Action:"artifact.upload",Reason:"",Previous:"previous",Current:"current",SourceIP:"",RequestID:"request",CreatedAtUnix:100,PreviousHash:""}
 preimage,err:=json.Marshal(event);if err!=nil{panic(err)};event.Hash=protocol.Hash(preimage);final,err:=json.Marshal(event);if err!=nil{panic(err)}
 if string(preimage)!=expected.Preimage||event.Hash!=expected.Hash||string(final)!=expected.Final{panic("historical Go audit encoding drift")}
 fmt.Println("PASS exact unversioned Go Event JSON bytes, empty hash preimage, plain SHA256 and final hash bytes unchanged")
}
