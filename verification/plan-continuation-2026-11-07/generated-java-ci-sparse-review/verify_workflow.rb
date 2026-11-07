require 'yaml'
require 'json'
old = YAML.safe_load(File.read(ARGV[0]), aliases: true)
prepared = YAML.safe_load(File.read(ARGV[1]), aliases: true)
fragment = YAML.safe_load(File.read(ARGV[2]), aliases: true)
raise 'Unexpected fragment jobs' unless fragment.keys == ['android-generated-java']
raise 'Added job differs from reviewed fragment' unless prepared.fetch('jobs').fetch('android-generated-java') == fragment.fetch('android-generated-java')
remainder = Marshal.load(Marshal.dump(prepared))
remainder.fetch('jobs').delete('android-generated-java')
raise 'Existing workflow semantics changed' unless remainder == old
raise 'Job count differs' unless old.fetch('jobs').length == 6 && prepared.fetch('jobs').length == 7
puts JSON.generate({status:'PASS', old_jobs:old.fetch('jobs').keys, added_job:'android-generated-java', full_existing_workflow_equal:true, added_job_equals_reviewed_fragment:true})
