package dev.mixer.compose

import android.os.Bundle
import android.widget.FrameLayout
import androidx.activity.ComponentActivity

class RuntimeActivity : ComponentActivity() {
    private lateinit var session: SwiftSession
    internal lateinit var bridge: JoinBridge
        private set
    internal lateinit var host: ComposeDocumentHost
        private set
    private val owners = mutableMapOf<java.util.UUID, StageOwner>()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        session = SwiftSession()
        bridge = JoinBridge(session)
        host = ComposeDocumentHost(window, bridge)
        setContentView(host)
    }

    internal fun prepare(step: Step): PrepareReceipt {
        val proposal = bridge.frame(step)
        val echo = proposal.echo
        val owner = owners.getOrPut(echo.owner) { host.newStageOwner(echo.owner) }
        return checkNotNull(host.prepare(owner, echo.sequence, echo.revision, echo.opaque,
            proposal.document, proposal.generations)).also { check(Echo(it) == echo) }
    }

    internal fun detachHost() = setContentView(FrameLayout(this))

    override fun onDestroy() {
        if (::session.isInitialized) {
            detachHost()
            session.close()
        }
        super.onDestroy()
    }
}
