{
  translate = {
    add_requirements = "requirementsExtra";
    disable_checks = "tests";
    extra_pkgs = "packagesExtra";
    overrides_pre = "overridesPre";
    overrides_post = "overridesPost";
    _provider_defaults = "_providerDefaults";
  };
  transform = {
    disable_checks = arg: ! arg;
  };
}
