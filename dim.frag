#version 300 es

precision mediump float;
in vec2 v_texcoord;
layout(location = 0) out vec4 fragColor;
uniform sampler2D tex;

void main() {
    vec4 pixColor = texture(tex, v_texcoord);

    float factor = 0.5; // lower = darker, higher = brighter

    fragColor = vec4(pixColor.rgb * factor, pixColor.a);
}
