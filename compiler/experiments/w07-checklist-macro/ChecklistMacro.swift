import SwiftSyntax
import SwiftSyntaxBuilder
import SwiftSyntaxMacros

public struct ChecklistCountMacro: ExpressionMacro {
    public static func expansion(
        of node: some FreestandingMacroExpansionSyntax,
        in context: some MacroExpansionContext
    ) throws -> ExprSyntax {
        guard node.arguments.count == 1, let mask = node.arguments.first?.expression else {
            throw MacroExpansionErrorMessage("expected one checklist mask")
        }
        return "boundedChecklistCount(\(mask.trimmed))"
    }
}
