from anagramist.utilities import geometricish_mean


class TestGeometricish:
    def test_positive_ints(self):
        data = [54, 24, 36]
        assert round(geometricish_mean(data), 3) == 36.809

    def test_positive_floats(self):
        data = [9.06, 30.54, 87.96, 118.29]
        assert round(geometricish_mean(data), 3) == 45.842

    def test_negative_floats(self):
        data = [-9.06, -30.0 - 54, -87.96, -118.29]
        assert round(geometricish_mean(data), 3) == -100.606

    def test_mixed_floats(self):
        data = [-9.06, 30.0 - 54, 87.96, -118.29]
        assert round(geometricish_mean(data), 3) == -80.879
