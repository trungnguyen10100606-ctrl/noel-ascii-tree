"""Final rotation paced to the reference Reel."""
import math

from render_v2 import smoothstep
from render_v3 import ProjectedRenderer, main


class ReferencePacedRenderer(ProjectedRenderer):
    def angle_at(self, t):
        return math.radians(17.76)*(t-14.8)

    def calm_at(self, t):
        return float(smoothstep((t-14.35)/1.18))


if __name__ == '__main__':
    main(ReferencePacedRenderer,
         review_times=[12.8, 14.8, 15.7, 16.6, 17.5, 18.4, 19.4, 20.5, 22.2, 23.8],
         crf='18')
