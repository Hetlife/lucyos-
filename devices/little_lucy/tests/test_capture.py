import unittest

from devices.little_lucy.platforms.nebula.native.capture import (
    DEFAULT_TTL_SECONDS,
    Frame,
    Geometry,
    NATIVE_HEIGHT,
    NATIVE_WIDTH,
    frame_metadata,
    is_fresh,
    map_native_to_pc,
    native_to_region,
)


class CaptureTests(unittest.TestCase):
    def test_identity_mapping_corners_and_centre(self):
        geometry = Geometry(width=NATIVE_WIDTH, height=NATIVE_HEIGHT)
        self.assertEqual(map_native_to_pc((0, 0), geometry), (0.0, 0.0))
        self.assertEqual(map_native_to_pc((NATIVE_WIDTH, NATIVE_HEIGHT), geometry), (float(NATIVE_WIDTH), float(NATIVE_HEIGHT)))
        self.assertEqual(map_native_to_pc((NATIVE_WIDTH / 2, NATIVE_HEIGHT / 2), geometry), (240.0, 136.0))

    def test_offset_and_scaled_region_maps_correctly(self):
        geometry = Geometry(x=100, y=50, width=960, height=544, scale=2)
        self.assertEqual(map_native_to_pc((0, 0), geometry), (100.0, 50.0))
        self.assertEqual(map_native_to_pc((240, 136), geometry), (580.0, 322.0))
        self.assertEqual(map_native_to_pc((480, 272), geometry), (1060.0, 594.0))

    def test_clamping_out_of_range_native_points(self):
        geometry = Geometry()
        self.assertEqual(map_native_to_pc((-10, -20), geometry), (0.0, 0.0))
        self.assertEqual(map_native_to_pc((9999, 9999), geometry), (1920.0, 1080.0))

    def test_native_to_region_returns_normalized_offsets(self):
        geometry = Geometry(x=100, y=50, width=960, height=544)
        self.assertEqual(native_to_region((0, 0), geometry), (0.0, 0.0))
        self.assertEqual(native_to_region((240, 136), geometry), (0.5, 0.5))
        self.assertEqual(native_to_region((9999, -1), geometry), (1.0, 0.0))

    def test_geometry_from_dict_defaults_and_rejects_bad_values(self):
        geometry = Geometry.from_dict({})
        self.assertEqual(geometry.to_dict(), {
            'x': 0.0,
            'y': 0.0,
            'width': 1920.0,
            'height': 1080.0,
            'scale': 1.0,
            'display_id': 'primary',
        })
        with self.assertRaises(ValueError):
            Geometry.from_dict({'width': 0})
        with self.assertRaises(ValueError):
            Geometry.from_dict({'height': -1})
        with self.assertRaises(ValueError):
            Geometry.from_dict({'scale': 0})
        with self.assertRaises(ValueError):
            Geometry.from_dict({'x': 'nope'})

    def test_frame_metadata_omits_image_bytes_and_reports_geometry(self):
        geometry = Geometry(x=10, y=20, width=30, height=40, display_id='display-1')
        frame = Frame(b'abc', 123.5, geometry, 30, 40)
        meta = frame_metadata(frame)
        self.assertEqual(meta['timestamp'], 123.5)
        self.assertEqual(meta['display_id'], 'display-1')
        self.assertEqual(meta['width'], 30.0)
        self.assertEqual(meta['height'], 40.0)
        self.assertEqual(meta['geometry'], geometry.to_dict())
        self.assertEqual(meta['bytes'], 3)
        self.assertNotIn('image_bytes', meta)

    def test_is_fresh_and_age(self):
        geometry = Geometry()
        frame = Frame(b'data', 10.0, geometry, 1, 1)
        self.assertAlmostEqual(frame.age(now=12.5), 2.5)
        self.assertTrue(is_fresh(frame, now=14.9, ttl=DEFAULT_TTL_SECONDS))
        self.assertFalse(is_fresh(frame, now=15.1, ttl=DEFAULT_TTL_SECONDS))

    def test_nan_and_inf_inputs_raise_value_error(self):
        geometry = Geometry()
        for point in ((float('nan'), 0), (0, float('inf')), ('x', 1)):
            with self.assertRaises(ValueError):
                map_native_to_pc(point, geometry)
            with self.assertRaises(ValueError):
                native_to_region(point, geometry)
        with self.assertRaises(ValueError):
            Geometry(x=float('nan'))
        with self.assertRaises(ValueError):
            Frame(b'', float('inf'), geometry, 1, 1)


if __name__ == '__main__':
    unittest.main()
