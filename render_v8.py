"""Silent Christmas cut with an animated code-built greeting."""
from greeting_v8 import paint_code_greeting
from render_v3 import main
from render_v7 import ColoredOrnamentRenderer


class CodeGreetingRenderer(ColoredOrnamentRenderer):
    def paint_title(self, frame, t):
        return paint_code_greeting(frame, t)


if __name__ == '__main__':
    main(CodeGreetingRenderer, review_times=[19.3, 22.5, 22.88, 23.19, 23.60,
                                              23.92, 24.22, 24.53, 24.89, 25.7],
         crf='18', duration=26)
