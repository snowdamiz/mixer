require "fileutils"
require "xcodeproj"

root = File.expand_path(ARGV.fetch(0))
project = Xcodeproj::Project.new(File.join(root, "GC4Differential.xcodeproj"))
app = project.new_target(:application, "GC4Differential", :ios, "17.0")
tests = project.new_target(:ui_test_bundle, "GC4DifferentialUITests", :ios, "17.0")
tests.add_dependency(app)

[app, tests].each do |target|
  target.build_configurations.each do |config|
    config.build_settings.merge!(
      "PRODUCT_BUNDLE_IDENTIFIER" => "dev.mixer.fixture." + target.name.downcase,
      "GENERATE_INFOPLIST_FILE" => "YES",
      "SWIFT_VERSION" => "6.0",
      "IPHONEOS_DEPLOYMENT_TARGET" => "17.0",
      "TARGETED_DEVICE_FAMILY" => "1"
    )
  end
end
app.build_configurations.each do |config|
  config.build_settings.merge!(
    "INFOPLIST_KEY_UILaunchScreen_Generation" => "YES",
    "INFOPLIST_KEY_UIApplicationSceneManifest_Generation" => "YES",
    "OTHER_LDFLAGS" => %w[-lGC4AppleFeature -lGC4MixerFeature -lMixerApple -lMixerSwiftUI -lMixerUI -lMixerCore]
  )
end
tests.build_configurations.each { |config| config.build_settings["TEST_TARGET_NAME"] = app.name }

sources = File.join(root, "Experiment")
FileUtils.mkdir(sources)
group = project.main_group.new_group("Experiment", "Experiment")
{ app => "DifferentialApp.swift", tests => "DifferentialUITests.swift" }.each do |target, name|
  FileUtils.cp(File.join(__dir__, name), sources)
  target.add_file_references([group.new_file(name)])
end
project.save
scheme = Xcodeproj::XCScheme.new
scheme.configure_with_targets(app, tests, launch_target: true)
scheme.save_as(project.path, app.name, true)
