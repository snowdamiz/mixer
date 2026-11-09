import Foundation

// Activity contexts are app lifetimes, never SDK owner identities. One request
// per context is outstanding until its exact reply is consumed or it is closed.
final class ActivityMailbox: @unchecked Sendable {
  struct Ticket: Sendable, Equatable {
    let context: Int64
    let request: String
  }
  private struct Context {
    var open = true
    var ticket: Ticket?
    var reply: String?
  }
  private let lock = NSLock()
  private var contexts: [Int64: Context] = [:]

  func register(_ context: Int64) -> Bool {
    lock.lock(); defer { lock.unlock() }
    guard context > 0, contexts[context] == nil else { return false }
    contexts[context] = Context()
    return true
  }
  func isOpen(_ context: Int64) -> Bool {
    lock.lock(); defer { lock.unlock() }
    return contexts[context]?.open == true
  }
  func reserve(_ context: Int64, request: String) -> Ticket? {
    lock.lock(); defer { lock.unlock() }
    guard !request.isEmpty, var state = contexts[context], state.open,
          state.ticket == nil else { return nil }
    let ticket = Ticket(context: context, request: request)
    state.ticket = ticket; contexts[context] = state
    return ticket
  }
  func accepts(_ ticket: Ticket) -> Bool {
    lock.lock(); defer { lock.unlock() }
    return contexts[ticket.context]?.open == true && contexts[ticket.context]?.ticket == ticket
  }
  func complete(_ ticket: Ticket, reply: String) {
    lock.lock(); defer { lock.unlock() }
    guard var state = contexts[ticket.context], state.open, state.ticket == ticket else { return }
    state.reply = reply; contexts[ticket.context] = state
  }
  func hasReply(_ context: Int64, request: String) -> Bool {
    lock.lock(); defer { lock.unlock() }
    guard let state = contexts[context], state.open,
          state.ticket?.request == request else { return false }
    return state.reply != nil
  }
  func take(_ context: Int64, request: String, capacity: Int) -> String? {
    lock.lock(); defer { lock.unlock() }
    guard var state = contexts[context], state.open,
          state.ticket?.request == request, let reply = state.reply,
          reply.utf8.count <= capacity else { return nil }
    state.reply = nil; state.ticket = nil; contexts[context] = state
    return reply
  }
  func cancel(_ context: Int64) -> Bool {
    lock.lock(); defer { lock.unlock() }
    guard var state = contexts[context], state.open else { return false }
    state.open = false; state.ticket = nil; state.reply = nil
    contexts[context] = state
    return true
  }
  func release(_ context: Int64) {
    lock.lock(); defer { lock.unlock() }
    precondition(contexts[context]?.open == false)
    contexts.removeValue(forKey: context)
  }
  var retainedCount: Int {
    lock.lock(); defer { lock.unlock() }
    return contexts.count
  }
}
