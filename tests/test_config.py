import yaml
import test_base
from xtlib.impl_utilities import ImplUtilities
from xtlib.impl_shared import ImplShared
from xtlib.helpers import xt_config


class TestConfig(test_base.TestBase):

	def setup_class(cls):
		internal_text_file = open("tests/fixtures/internal.yaml", "r")
		cls.internal_text = internal_text_file.read()
		internal_text_file.close()
		print("Setup Class")

	def teardown_class(cls):
		cls.internal_text = None
		print("Teardown class")

	def setup(self):
		print("Setup for test")

	def teardown(self):
		print("Teardown for test")

	def test_config_merge(self):
		original_config = xt_config.get_merged_config()
		assert("compute-targets" in original_config.data)
		assert("aml-internal" not in original_config.data["compute-targets"])
		result_yaml_text = xt_config.get_merged_internal_xt_config_string(self.internal_text)
		result = yaml.safe_load(result_yaml_text)
		assert("compute-targets" in result)
		assert("aml-internal" in result["compute-targets"])

	def test_philly_templates(self):
		impl_shared = ImplShared()
		impl_utilities = ImplUtilities(xt_config.XTConfig(), impl_shared.store)
		result = yaml.safe_load(impl_utilities.get_config_template("philly"))
		assert(result)
		assert("external-services" in result)
		self.assert_keys(result, ["external-services", "xt-services", "compute-targets", "dockers", "setups"])
		external_services = result["external-services"]
		self.assert_keys(external_services, ["philly", "philly-registry"])
		xt_services = result["xt-services"]
		self.assert_keys(xt_services, ["storage", "mongo", "vault", "target"])
