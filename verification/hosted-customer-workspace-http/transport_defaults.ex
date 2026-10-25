# Standalone transport-collector declarations only. These deliberately cannot
# qualify domain behavior; production no-auth route tests must never call them.
defmodule MixerHosted.CustomerWorkspace do
  def organizations(_, _), do: raise("standalone default facade must not be reached")
  def projects(_, _, _), do: raise("standalone default facade must not be reached")
end

defmodule MixerHosted.CustomerArtifacts do
  def upload_at(_, _, _, _, _, _), do: raise("standalone default facade must not be reached")
  def read(_, _, _, _), do: raise("standalone default facade must not be reached")
  def audit(_, _, _, _, _), do: raise("standalone default facade must not be reached")
end
