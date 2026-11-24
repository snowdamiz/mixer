require "xcodeproj"

root = File.expand_path(ARGV.fetch(0))
project = Xcodeproj::Project.new(File.join(root, "UP5Theme.xcodeproj"))
app = project.new_target(:application, "UP5Theme", :ios, "17.0")
test = project.new_target(:ui_test_bundle, "UP5ThemeUITests", :ios, "17.0")
test.add_dependency(app)
test.build_configurations.each { |config| config.build_settings["TEST_TARGET_NAME"] = app.name }

[app, test].each do |target|
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
  config.build_settings["INFOPLIST_KEY_UILaunchScreen_Generation"] = "YES"
  config.build_settings["INFOPLIST_KEY_UIApplicationSceneManifest_Generation"] = "YES"
end
group = project.main_group.new_group("Experiment", "Experiment")
%w[UP5ThemeApp.swift SignedFixture.swift FixtureTheme.swift GuestUISignedProgram.swift HeldPressProbe.swift ThemePixels.swift].each do |file|
  app.add_file_references([group.new_file(file)])
end
%w[UP5ThemeUITests.swift ThemePixels.swift].each do |file|
  test.add_file_references([group.new_file(file)])
end
app.resources_build_phase.add_file_reference(group.new_file("Fixtures", :group).tap do |ref|
  ref.last_known_file_type = "folder"
end)

{
  "capability-activation" => %w[MixerCapabilityActivation],
  "runtime-identity" => %w[MixerRuntimeIdentity],
  "sdk" => %w[MixerApple MixerCapabilities MixerUI],
  "updates" => %w[MixerUpdates],
}.each do |directory, products|
  ref = project.new(Xcodeproj::Project::Object::XCLocalSwiftPackageReference)
  ref.relative_path = "mixer/" + directory
  project.root_object.package_references << ref
  products.each do |name|
    dependency = project.new(Xcodeproj::Project::Object::XCSwiftPackageProductDependency)
    dependency.package = ref
    dependency.product_name = name
    app.package_product_dependencies << dependency
    app.frameworks_build_phase.files << project.new(Xcodeproj::Project::Object::PBXBuildFile).tap do |file|
      file.product_ref = dependency
    end
  end
end

project.save
scheme = Xcodeproj::XCScheme.new
scheme.configure_with_targets(app, test, launch_target: true)
scheme.save_as(project.path, app.name, true)
