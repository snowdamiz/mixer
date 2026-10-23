import Foundation
let modes: [(String, GuestProgram.Mode)] = [("storage",.storage),("trap",.trap),("spin",.spin),("unconsumed",.unconsumed),("burst0",.burst(0)),("burst1",.burst(1)),("burst8",.burst(8)),("single0",.single(0,Data())),("single1",.single(1,GuestProgram.get)),("single2",.single(2,GuestProgram.put)),("single3",.single(3,Data(repeating:255,count:256)))]
for (name,mode) in modes { print(name+" "+GuestProgram.build(mode).base64EncodedString()) }
