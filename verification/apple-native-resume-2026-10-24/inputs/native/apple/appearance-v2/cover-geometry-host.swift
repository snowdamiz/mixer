import Foundation
@main struct CoverGeometryDefinitions {
    static func main() throws {
        let outcomes = try AppearanceCoverGeometryRegressionV2.pure()
        let data = outcomes.map { ["name":$0.name,"passed":$0.passed] as [String:Any] }
        print(String(data:try JSONSerialization.data(withJSONObject:data,options:[.prettyPrinted,.sortedKeys]),encoding:.utf8)!)
        guard outcomes.allSatisfy(\.passed) else { throw NSError(domain:"CoverGeometryDefinitions",code:1) }
    }
}
