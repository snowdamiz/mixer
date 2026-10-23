import Foundation
import MixerRuntimeIdentity
do { let value = try MixerInstalledCapabilityRuntime.load(); print(value.fingerprint); print(value.installedRuntime.protocolVersion); print(value.installedRuntime.guestABI); print(value.capabilityExecution.route); print(value.capabilities.count) } catch { FileHandle.standardError.write(Data(String(describing:error).utf8)); exit(3) }
