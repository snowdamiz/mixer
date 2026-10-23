"""Adversarial checks of the design codec oracle; no product or render claims."""
import copy
import json
import unittest
from validate_descriptor import HERE, DescriptorError, canonical, decode

class DescriptorTests(unittest.TestCase):
    def setUp(self):
        self.raw = (HERE / 'mixer-default-appearance-v1.json').read_bytes()
        self.value = json.loads(self.raw)

    def bad(self, data):
        with self.assertRaises(DescriptorError): decode(data)

    def mutate(self, change):
        value = copy.deepcopy(self.value)
        change(value)
        self.bad(canonical(value))

    def resource(self, identifier='font.regular'):
        return dict(id=identifier,kind='fontSFNT',path=identifier+'.ttf',sha256='a'*64,bytes=1,
                    provenance='Fixture metadata only; no actual font bytes',scale=1,locale='und',direction='neutral')

    def bundled(self):
        value = copy.deepcopy(self.value)
        value['resources'] = [self.resource('regular'),self.resource('semibold')]
        value['theme']['typography']['font'] = dict(kind='bundled',fallback='none',faces=[
            dict(resourceID='regular',postScriptName='Fixture-Regular',weight=400,style='normal'),
            dict(resourceID='semibold',postScriptName='Fixture-Semibold',weight=600,style='normal')])
        return value

    def test_default_roundtrip(self):
        self.assertEqual(canonical(decode(self.raw)), self.raw)

    def test_explicit_platform_mode(self):
        value = self.value
        theme = value.pop('theme')
        value.update(mode='platformSpecific',iOS=theme,android=copy.deepcopy(theme),reason='Explicit app choice')
        self.assertEqual(decode(canonical(value))['mode'],'platformSpecific')

    def test_bundled_metadata_is_not_resource_validation(self):
        value = self.bundled()
        self.assertEqual(decode(canonical(value)), value)

    def test_raw_duplicate(self): self.bad(self.raw.replace(b'"mode":"shared"',b'"mode":"shared","mode":"shared"'))
    def test_escaped_duplicate(self): self.bad(self.raw.replace(b'"mode":"shared"',b'"mode":"shared","m\\u006fde":"shared"'))
    def test_unknown_root(self): self.mutate(lambda v: v.update(downloadURL='https://example.invalid/theme'))
    def test_unknown_nested(self): self.mutate(lambda v: v['theme']['controls'].update(toolkitStyle='automatic'))
    def test_missing_nested(self): self.mutate(lambda v: v['theme']['light'].pop('accent'))
    def test_wrong_mode_fields(self): self.mutate(lambda v: v.update(reason='implicit'))
    def test_boolean_not_integer(self): self.mutate(lambda v: v['theme']['layout'].update(stackGap64=True))
    def test_negative_token(self): self.bad(self.raw.replace(b'"stackGap64":512',b'"stackGap64":-1'))
    def test_negative_zero_token(self): self.bad(self.raw.replace(b'"rowGap64":0',b'"rowGap64":-0'))
    def test_fraction_token(self): self.bad(self.raw.replace(b'"stackGap64":512',b'"stackGap64":512.0'))
    def test_exponent_token(self): self.bad(self.raw.replace(b'"stackGap64":512',b'"stackGap64":512e0'))
    def test_nan_token(self): self.bad(self.raw.replace(b'"stackGap64":512',b'"stackGap64":NaN'))
    def test_metric_range(self): self.mutate(lambda v: v['theme']['layout'].update(stackGap64=65537))
    def test_opacity_range(self): self.mutate(lambda v: v['theme']['controls'].update(pressedOpacityPermille=1001))
    def test_color_case(self): self.mutate(lambda v: v['theme']['light'].update(accent='#007affFF'))
    def test_short_color(self): self.mutate(lambda v: v['theme']['light'].update(accent='#007AFF'))
    def test_short_line_box(self): self.mutate(lambda v: v['theme']['typography']['body'].update(minimumLineBox64=64))
    def test_toggle_geometry(self): self.mutate(lambda v: v['theme']['controls']['toggle'].update(thumb64=2000))
    def test_bad_utf8(self): self.bad(b'\xff'+self.raw)
    def test_unpaired_surrogate(self): self.bad(self.raw.replace(b'"mixer.default.v1"',b'"\\ud800"'))
    def test_non_ascii(self): self.mutate(lambda v: v.update(id='app.\u00e9'))
    def test_bom(self): self.bad(b'\xef\xbb\xbf'+self.raw)
    def test_noncanonical_space(self): self.bad(b' '+self.raw)
    def test_missing_final_lf(self): self.bad(self.raw[:-1])
    def test_extra_final_lf(self): self.bad(self.raw+b'\n')
    def test_trailing_data(self): self.bad(self.raw+b'{}')
    def test_oversize(self): self.bad(b' '*65537)
    def test_depth_preflight(self): self.bad(b'['*17+b'0'+b']'*17)
    def test_missing_resource(self):
        value=self.bundled(); value['resources'].pop(); self.bad(canonical(value))
    def test_wrong_resource_kind(self):
        value=self.bundled(); value['resources'][0]['kind']='iconPNG'; self.bad(canonical(value))
    def test_wrong_weight_even_with_fallback(self):
        value=self.bundled(); value['theme']['typography']['font']['faces'].pop()
        value['theme']['typography']['font']['fallback']='systemSans'; self.bad(canonical(value))
    def test_implicit_fallback(self):
        value=self.bundled(); value['theme']['typography']['font'].pop('fallback'); self.bad(canonical(value))
    def test_duplicate_face(self):
        value=self.bundled(); value['theme']['typography']['font']['faces'].append(value['theme']['typography']['font']['faces'][0]); self.bad(canonical(value))
    def test_duplicate_resource(self):
        value=self.bundled(); value['resources'].append(value['resources'][0]); self.bad(canonical(value))
    def test_duplicate_path(self):
        value=self.bundled(); value['resources'][1]['path']=value['resources'][0]['path']; self.bad(canonical(value))
    def test_path_escape(self):
        value=self.bundled(); value['resources'][0]['path']='../font.ttf'; self.bad(canonical(value))
    def test_font_variant(self):
        value=self.bundled(); value['resources'][0]['direction']='rightToLeft'; self.bad(canonical(value))
    def test_path_case_collision(self):
        value=self.bundled(); value['resources'][1]['path']=value['resources'][0]['path'].upper(); self.bad(canonical(value))
    def test_invalid_sha256(self):
        value=self.bundled(); value['resources'][0]['sha256']='A'*64; self.bad(canonical(value))
    def test_zero_resource_bytes(self):
        value=self.bundled(); value['resources'][0]['bytes']=0; self.bad(canonical(value))
    def test_resource_count(self):
        value=self.value; value['resources']=[self.resource('r'+str(i)) for i in range(65)]; self.bad(canonical(value))
    def test_font_count(self):
        value=self.value; value['resources']=[self.resource('r'+str(i)) for i in range(17)]; self.bad(canonical(value))
    def test_resource_total(self):
        value=self.value; value['resources']=[self.resource('r'+str(i)) for i in range(5)]
        for resource in value['resources']: resource['bytes']=4194304
        self.bad(canonical(value))
    def test_implicit_font(self): self.mutate(lambda v: v['theme']['typography'].update(font=dict(kind='automatic')))
    def test_reason_whitespace(self):
        value=self.value; theme=value.pop('theme'); value.update(mode='platformSpecific',iOS=theme,android=theme,reason=' '); self.bad(canonical(value))
    def test_escaped_noncanonical_id(self): self.bad(self.raw.replace(b'mixer.default.v1',b'mixer.default.v\\u0031'))
    def test_unsupported_weight(self): self.mutate(lambda v: v['theme']['typography']['body'].update(weight=450))

if __name__ == '__main__': unittest.main(verbosity=2)
