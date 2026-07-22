"""Unit tests for GpxAnalyzer — no DB, no network."""



from terratrain.services.gpx_analyzer import GpxAnalyzer

FLAT_GPX = """<?xml version="1.0"?>
<gpx version="1.1" xmlns="http://www.topografix.com/GPX/1/1">
  <trk><trkseg>
    <trkpt lat="47.0" lon="8.0"><ele>500</ele></trkpt>
    <trkpt lat="47.01" lon="8.01"><ele>502</ele></trkpt>
    <trkpt lat="47.02" lon="8.02"><ele>504</ele></trkpt>
  </trkseg></trk>
</gpx>"""

HILLY_GPX = """<?xml version="1.0"?>
<gpx version="1.1" xmlns="http://www.topografix.com/GPX/1/1">
  <trk><trkseg>
    <trkpt lat="47.0" lon="8.0"><ele>400</ele></trkpt>
    <trkpt lat="47.001" lon="8.001"><ele>420</ele></trkpt>
    <trkpt lat="47.002" lon="8.002"><ele>450</ele></trkpt>
    <trkpt lat="47.003" lon="8.003"><ele>480</ele></trkpt>
    <trkpt lat="47.004" lon="8.004"><ele>510</ele></trkpt>
    <trkpt lat="47.005" lon="8.005"><ele>540</ele></trkpt>
    <trkpt lat="47.006" lon="8.006"><ele>560</ele></trkpt>
    <trkpt lat="47.007" lon="8.007"><ele>570</ele></trkpt>
  </trkseg></trk>
</gpx>"""


def test_flat_route_returns_valid_result():
    result = GpxAnalyzer.analyze(FLAT_GPX)
    assert result["distance_m"] > 0
    assert result["elevation_gain_m"] >= 0
    assert isinstance(result["climb_profile"], list)
    assert 0.0 <= result["terrain_score"] <= 1.0


def test_empty_gpx_returns_zeros():
    empty = """<?xml version="1.0"?>
    <gpx version="1.1" xmlns="http://www.topografix.com/GPX/1/1"><trk><trkseg></trkseg></trk></gpx>"""
    result = GpxAnalyzer.analyze(empty)
    assert result["distance_m"] == 0.0
    assert result["climb_profile"] == []


def test_haversine_known_distance():
    # ~94 km straight-line between Bern and Zurich
    d = GpxAnalyzer._haversine(46.95, 7.45, 47.37, 8.54)
    assert 85_000 < d < 110_000


def test_terrain_score_bounds():
    for gain in [0, 500, 1000, 5000]:
        for dist in [1000, 10000, 100000]:
            score = GpxAnalyzer._compute_terrain_score(gain, dist, [])
            assert 0.0 <= score <= 1.0, f"Score out of bounds for gain={gain}, dist={dist}"


def test_classify_climb_hc():
    category = GpxAnalyzer._classify_climb(ele_gain_m=1500, avg_grade_pct=8.0)
    assert category == "hc"


def test_classify_climb_cat4():
    category = GpxAnalyzer._classify_climb(ele_gain_m=100, avg_grade_pct=5.0)
    assert category in {"cat4", None}


def test_elevation_smoothing_reduces_noise():
    spikey_gpx = """<?xml version="1.0"?>
    <gpx version="1.1" xmlns="http://www.topografix.com/GPX/1/1">
      <trk><trkseg>
        <trkpt lat="47.0" lon="8.0"><ele>500</ele></trkpt>
        <trkpt lat="47.001" lon="8.001"><ele>520</ele></trkpt>
        <trkpt lat="47.002" lon="8.002"><ele>500</ele></trkpt>
        <trkpt lat="47.003" lon="8.003"><ele>520</ele></trkpt>
        <trkpt lat="47.004" lon="8.004"><ele>500</ele></trkpt>
      </trkseg></trk>
    </gpx>"""
    result = GpxAnalyzer.analyze(spikey_gpx)
    assert result["max_elevation_m"] < 520.0
    assert result["min_elevation_m"] > 500.0
    # Spikey gain without smoothing would be 40.0. With smoothing it is around 5.4.
    assert result["elevation_gain_m"] < 15.0

