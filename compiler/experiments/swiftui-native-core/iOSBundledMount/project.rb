require "fileutils"
require "xcodeproj"

root = File.expand_path(ARGV.fetch(0))
fixture = File.expand_path(__dir__)
project = Xcodeproj::Project.new(File.join(root, "UP5Bundled.xcodeproj"))
app = project.new_target(:application, "UP5Bundled", :ios, "17.0")
tests = project.new_target(:unit_test_bundle, "UP5BundledTests", :ios, "17.0")
ui_tests = project.new_target(:ui_test_bundle, "UP5BundledUITests", :ios, "17.0")
[tests, ui_tests].each { |target| target.add_dependency(app) }

[app, tests, ui_tests].each do |target|
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
    "DEAD_CODE_STRIPPING" => "NO",
    "OTHER_LDFLAGS" => %w[-lUP5StarterFeature -lMixerApple -lMixerSwiftUI -lMixerUI -lMixerCore]
  )
end
tests.build_configurations.each do |config|
  config.build_settings["TEST_HOST"] = "$(BUILT_PRODUCTS_DIR)/#{app.name}.app/#{app.name}"
  config.build_settings["BUNDLE_LOADER"] = "$(TEST_HOST)"
  config.build_settings["OTHER_SWIFT_FLAGS"] = ["-package-name", "Mixer"]
end
ui_tests.build_configurations.each { |config| config.build_settings["TEST_TARGET_NAME"] = app.name }

# The hosted target's generated xctestrun injects this from the app's Frameworks directory.
injector = project.main_group.new_file("Developer/usr/lib/libXCTestBundleInject.dylib")
injector.source_tree = "PLATFORM_DIR"
embed = app.new_copy_files_build_phase("Embed XCTest Injector")
embed.symbol_dst_subfolder_spec = :frameworks
embed.add_file_reference(injector).settings = { "ATTRIBUTES" => ["CodeSignOnCopy"] }

sources = File.join(root, "Experiment")
FileUtils.mkdir(sources)
group = project.main_group.new_group("Experiment", "Experiment")
{ app => "BundledApp.swift", tests => "BundledMountTests.swift", ui_tests => "BundledUITests.swift" }.each do |target, name|
  FileUtils.cp(File.join(fixture, name), sources)
  target.add_file_references([group.new_file(name)])
end
project.save
scheme = Xcodeproj::XCScheme.new
scheme.configure_with_targets(app, tests, launch_target: true)
scheme.add_test_target(ui_tests)
scheme.save_as(project.path, app.name, true)
