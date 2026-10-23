// Original narrow consumer: New/Close only, never opens an HTTP listener.
package main

import (
	"fmt"
	"mixer/services/protocol"
	"mixer/services/release"
	"os"
)

func main() {
	raw, e := os.ReadFile(os.Args[1])
	if e != nil {
		panic(e)
	}
	var cfg release.Config
	if e = protocol.DecodeJSON(raw, &cfg); e != nil {
		panic(e)
	}
	server, e := release.New(cfg)
	if e != nil {
		panic(e)
	}
	if e = server.Close(); e != nil {
		panic(e)
	}
	fmt.Println("updated service accepted schema3 container without HTTP startup")
}
