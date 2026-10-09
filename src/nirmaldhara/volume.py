"""Stored water volume from depth, for a real road profile (METHOD.md section 15.1).

The profile is a list of (distance_m, height_m) points along the road through
the dip. The ponded length at a given water height is piecewise linear in that
height, so volume is piecewise quadratic. Volumes at each profile height are
computed once; a lookup is then a binary search plus one closed-form step.
"""

from bisect import bisect_right
from math import sqrt


class VolumeCurve:
    def __init__(self, profile, width_m):
        points = sorted(profile)
        if len(points) < 2:
            raise ValueError("a profile needs at least two points")
        self.width = width_m
        self.segments = list(zip(points, points[1:]))
        base = min(h for _, h in points)
        # Breakpoints: heights above the lowest point at which the shape changes.
        self.heights = sorted({h - base for _, h in points})
        self.base = base
        self.lengths = [self._length(z) for z in self.heights]
        self.volumes = [0.0]
        for i in range(1, len(self.heights)):
            dz = self.heights[i] - self.heights[i - 1]
            mean_length = (self.lengths[i] + self.lengths[i - 1]) / 2
            self.volumes.append(self.volumes[-1] + width_m * mean_length * dz)
        self.max_depth = self.heights[-1]

    def _length(self, z):
        """Horizontal length of road lying at or below water height z."""
        total = 0.0
        for (x1, h1), (x2, h2) in self.segments:
            low, high = min(h1, h2) - self.base, max(h1, h2) - self.base
            if z >= high:
                total += x2 - x1
            elif z > low:
                total += (x2 - x1) * (z - low) / (high - low)
        return total

    def volume(self, depth_m):
        """Cubic metres stored when the water is depth_m deep at the lowest point."""
        d = min(max(depth_m, 0.0), self.max_depth)
        i = max(bisect_right(self.heights, d) - 1, 0)
        if i >= len(self.heights) - 1:
            return self.volumes[-1]
        z0, z1 = self.heights[i], self.heights[i + 1]
        l0, l1 = self.lengths[i], self.lengths[i + 1]
        dz = d - z0
        slope = (l1 - l0) / (z1 - z0)
        return self.volumes[i] + self.width * (l0 * dz + slope * dz * dz / 2)

    def depth(self, volume_m3):
        """Inverse of volume(): the depth at which this much water is stored."""
        v = min(max(volume_m3, 0.0), self.volumes[-1])
        i = max(bisect_right(self.volumes, v) - 1, 0)
        if i >= len(self.heights) - 1:
            return self.max_depth
        z0, z1 = self.heights[i], self.heights[i + 1]
        l0, l1 = self.lengths[i], self.lengths[i + 1]
        slope = (l1 - l0) / (z1 - z0)
        rest = (v - self.volumes[i]) / self.width      # = l0*dz + slope*dz^2/2
        if abs(slope) < 1e-12:
            return z0 + (rest / l0 if l0 else 0.0)
        return z0 + (-l0 + sqrt(l0 * l0 + 2 * slope * rest)) / slope
