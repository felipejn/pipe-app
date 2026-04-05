import colorsys
import re
from flask import render_template, request, jsonify
from flask_login import login_required
from app.cores import bp


# Swatches Material Design — cores hex em 0xRRGGBB
MATERIAL_SWATCHES = {
    'red':        { 50: 0xFFEBEE, 100: 0xFFCDD2, 200: 0xEF9A9A, 300: 0xE57373, 400: 0xEF5350, 500: 0xF44336, 600: 0xE53935, 700: 0xD32F2F, 800: 0xC62828, 900: 0xB71C1C },
    'pink':       { 50: 0xFCE4EC, 100: 0xF8BBD0, 200: 0xF48FB1, 300: 0xF06292, 400: 0xEC407A, 500: 0xE91E63, 600: 0xD81B60, 700: 0xC2185B, 800: 0xAD1457, 900: 0x880E4F },
    'purple':     { 50: 0xF3E5F5, 100: 0xE1BEE7, 200: 0xCE93D8, 300: 0xBA68C8, 400: 0xAB47BC, 500: 0x9C27B0, 600: 0x8E24AA, 700: 0x7B1FA2, 800: 0x6A1B9A, 900: 0x4A148C },
    'deepPurple': { 50: 0xEDE7F6, 100: 0xD1C4E9, 200: 0xB39DDB, 300: 0x9575CD, 400: 0x7E57C2, 500: 0x673AB7, 600: 0x5E35B1, 700: 0x512DA8, 800: 0x4527A0, 900: 0x311B92 },
    'indigo':     { 50: 0xE8EAF6, 100: 0xC5CAE9, 200: 0x9FA8DA, 300: 0x7986CB, 400: 0x5C6BC0, 500: 0x3F51B5, 600: 0x3949AB, 700: 0x303F9F, 800: 0x283593, 900: 0x1A237E },
    'blue':       { 50: 0xE3F2FD, 100: 0xBBDEFB, 200: 0x90CAF9, 300: 0x64B5F6, 400: 0x42A5F5, 500: 0x2196F3, 600: 0x1E88E5, 700: 0x1976D2, 800: 0x1565C0, 900: 0x0D47A1 },
    'lightBlue':  { 50: 0xE1F5FE, 100: 0xB3E5FC, 200: 0x81D4FA, 300: 0x4FC3F7, 400: 0x29B6F6, 500: 0x03A9F4, 600: 0x039BE5, 700: 0x0288D1, 800: 0x0277BD, 900: 0x01579B },
    'cyan':       { 50: 0xE0F7FA, 100: 0xB2EBF2, 200: 0x80DEEA, 300: 0x4DD0E1, 400: 0x26C6DA, 500: 0x00BCD4, 600: 0x00ACC1, 700: 0x0097A7, 800: 0x00838F, 900: 0x006064 },
    'teal':       { 50: 0xE0F2F1, 100: 0xB2DFDB, 200: 0x80CBC4, 300: 0x4DB6AC, 400: 0x26A69A, 500: 0x009688, 600: 0x00897B, 700: 0x00796B, 800: 0x00695C, 900: 0x004D40 },
    'green':      { 50: 0xE8F5E9, 100: 0xC8E6C9, 200: 0xA5D6A7, 300: 0x81C784, 400: 0x66BB6A, 500: 0x4CAF50, 600: 0x43A047, 700: 0x388E3C, 800: 0x2E7D32, 900: 0x1B5E20 },
    'lightGreen': { 50: 0xF1F8E9, 100: 0xDCEDC8, 200: 0xC5E1A5, 300: 0xAED581, 400: 0x9CCC65, 500: 0x8BC34A, 600: 0x7CB342, 700: 0x689F38, 800: 0x558B2F, 900: 0x33691E },
    'lime':       { 50: 0xF9FBE7, 100: 0xF0F4C3, 200: 0xE6EE9C, 300: 0xDCE775, 400: 0xD4E151, 500: 0xCDDC39, 600: 0xC0CA33, 700: 0xAFB42B, 800: 0x9E9D24, 900: 0x827717 },
    'yellow':     { 50: 0xFFFDE7, 100: 0xFFF9C4, 200: 0xFFF59D, 300: 0xFFF176, 400: 0xFFEE58, 500: 0xFFEB3B, 600: 0xFDD835, 700: 0xFBC02D, 800: 0xF9A825, 900: 0xF57F17 },
    'amber':      { 50: 0xFFF8E1, 100: 0xFFECB3, 200: 0xFFE081, 300: 0xFFD54F, 400: 0xFFCA28, 500: 0xFFC107, 600: 0xFFB300, 700: 0xFFA000, 800: 0xFF8F00, 900: 0xFF6F00 },
    'orange':     { 50: 0xFFF3E0, 100: 0xFFE0B2, 200: 0xFFCC80, 300: 0xFFB74D, 400: 0xFFA726, 500: 0xFF9800, 600: 0xFB8C00, 700: 0xF57C00, 800: 0xEF6C00, 900: 0xE65100 },
    'deepOrange': { 50: 0xFBE9E7, 100: 0xFFCCBC, 200: 0xFFAB91, 300: 0xFF8A65, 400: 0xFF7043, 500: 0xFF5722, 600: 0xF4511E, 700: 0xE64A19, 800: 0xD84315, 900: 0xBF360C },
    'brown':      { 50: 0xEFEBE9, 100: 0xD7CCC8, 200: 0xBCAAA4, 300: 0xA1887F, 400: 0x8D6E63, 500: 0x795548, 600: 0x6D4C41, 700: 0x5D4037, 800: 0x4E342E, 900: 0x3E2723 },
    'grey':       { 50: 0xFAFAFA, 100: 0xF5F5F5, 200: 0xEEEEEE, 300: 0xE0E0E0, 400: 0xBDBDBD, 500: 0x9E9E9E, 600: 0x757575, 700: 0x616161, 800: 0x424242, 900: 0x212121 },
    'blueGrey':   { 50: 0xECEFF1, 100: 0xCFD8DC, 200: 0xB0BEC5, 300: 0x90A4AE, 400: 0x78909C, 500: 0x607D8B, 600: 0x546E7A, 700: 0x455A64, 800: 0x37474F, 900: 0x263238 },
}

# Nome bonito para display
SWATCH_LABELS = {
    'red': 'Red', 'pink': 'Pink', 'purple': 'Purple', 'deepPurple': 'Deep Purple',
    'indigo': 'Indigo', 'blue': 'Blue', 'lightBlue': 'Light Blue', 'cyan': 'Cyan',
    'teal': 'Teal', 'green': 'Green', 'lightGreen': 'Light Green', 'lime': 'Lime',
    'yellow': 'Yellow', 'amber': 'Amber', 'orange': 'Orange', 'deepOrange': 'Deep Orange',
    'brown': 'Brown', 'grey': 'Grey', 'blueGrey': 'Blue Grey',
}


# ---- Conversoes de cores ----

def _hex_para_rgb(hex_val):
    hex_val = hex_val.lstrip('#')
    if len(hex_val) == 8:
        a = int(hex_val[6:8], 16)
        hex_val = hex_val[:6]
    elif len(hex_val) == 3:
        hex_val = hex_val[0]*2 + hex_val[1]*2 + hex_val[2]*2
    else:
        a = 255
    try:
        r = int(hex_val[0:2], 16)
        g = int(hex_val[2:4], 16)
        b = int(hex_val[4:6], 16)
    except (ValueError, IndexError):
        r, g, b = 255, 0, 0
    return r, g, b, a if len(hex_val) != 8 else 255


def _rgb_para_hex(r, g, b):
    return '#{:02X}{:02X}{:02X}'.format(r, g, b)


def _rgb_para_hsl(r, g, b):
    rn, gn, bn = r / 255.0, g / 255.0, b / 255.0
    h, l, s = colorsys.rgb_to_hls(rn, gn, bn)
    return round(h * 360), round(s * 100), round(l * 100)


def _rgb_para_hsv(r, g, b):
    rn, gn, bn = r / 255.0, g / 255.0, b / 255.0
    h, s, v = colorsys.rgb_to_hsv(rn, gn, bn)
    return round(h * 360), round(s * 100), round(v * 100)


def _hsl_para_rgb(h, s, l):
    rn, gn, bn = colorsys.hls_to_rgb(h / 360.0, l / 100.0, s / 100.0)
    return _clamp_rgb(rn, gn, bn)


def _hsv_para_rgb(h, s, v):
    rn, gn, bn = colorsys.hsv_to_rgb(h / 360.0, s / 100.0, v / 100.0)
    return _clamp_rgb(rn, gn, bn)


def _cmyk_para_rgb(c, m, y, k):
    c, m, y, k = c / 100.0, m / 100.0, y / 100.0, k / 100.0
    r = round(255 * (1 - c) * (1 - k))
    g = round(255 * (1 - m) * (1 - k))
    b = round(255 * (1 - y) * (1 - k))
    return max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b))


def _clamp_rgb(rn, gn, bn):
    return max(0, min(255, round(rn * 255))), max(0, min(255, round(gn * 255))), max(0, min(255, round(bn * 255)))


def _cor_material_mais_proxima(r, g, b, a=255):
    if a < 128:
        return None
    melhor_dist = float('inf')
    melhor_nome = melhor_shade = None
    for nome, shades in MATERIAL_SWATCHES.items():
        for shade_val, cor in shades.items():
            sr, sg, sb = (cor >> 16) & 0xFF, (cor >> 8) & 0xFF, cor & 0xFF
            dist = (sr - r) ** 2 + (sg - g) ** 2 + (sb - b) ** 2
            if dist < melhor_dist:
                melhor_dist = dist
                melhor_nome = nome
                melhor_shade = shade_val
    # Tolerancia: so mostra se realmente proximo
    if melhor_dist > 50000:
        return None
    return f'Colors.{SWATCH_LABELS.get(melhor_nome, melhor_nome)}[{melhor_shade}]'


def _flutter_para_rgb(codigo):
    codigo = codigo.strip()
    match = re.search(r'0x([0-9A-Fa-f]{6,8})', codigo)
    if not match:
        return None
    val_str = match.group(1)
    val = int(val_str, 16)
    if len(val_str) == 8:
        a = (val >> 24) & 0xFF
    else:
        a = 255
    r = (val >> 16) & 0xFF
    g = (val >> 8) & 0xFF
    b = val & 0xFF
    return r, g, b, a


def _converter_para_flutter(r, g, b, a=255):
    hex_rgb = _rgb_para_hex(r, g, b)
    alpha_f = round(a / 255.0, 2)
    h_hsl, s_hsl, l = _rgb_para_hsl(r, g, b)
    h_hsv, s_hsv, v = _rgb_para_hsv(r, g, b)
    material = _cor_material_mais_proxima(r, g, b, a)

    return {
        'hex': hex_rgb,
        'hex_argb': '#{:02X}{:02X}{:02X}{:02X}'.format(a, r, g, b),
        'color_hex': 'Color(0x{:02X}{:02X}{:02X}{:02X})'.format(a, r, g, b),
        'color_rgb': 'Color.fromRGBO({}, {}, {}, {})'.format(r, g, b, alpha_f),
        'color_argb': 'Color.fromARGB({}, {}, {}, {})'.format(a, r, g, b),
        'color_hsl': 'HSLColor.fromAHSL({}, {}, {}, {}).toColor()'.format(alpha_f, h_hsl, s_hsl, l),
        'color_hsv': 'HSVColor.fromAHSV({}, {}, {}, {}).toColor()'.format(alpha_f, h_hsv, s_hsv, v),
        'material': material,
        'opacidade': alpha_f,
        'css': 'rgb({}, {}, {})'.format(r, g, b) if a == 255 else 'rgba({}, {}, {}, {})'.format(r, g, b, alpha_f),
    }


# ---- Rotas ----

@bp.route('/')
@login_required
def index():
    return render_template('cores/index.html')


@bp.route('/api/convert', methods=['POST'])
@login_required
def api_convert():
    dados = request.get_json(force=True)
    modo = dados.get('modo', 'cor_para_flutter')

    if modo == 'flutter_para_cor':
        codigo = dados.get('codigo', '')
        resultado = _flutter_para_rgb(codigo)
        if resultado is None:
            return jsonify({'erro': 'Codigo Flutter nao reconhecido'}), 400
        r, g, b, a = resultado
        return jsonify({
            'r': r, 'g': g, 'b': b, 'a': a,
            'hex': _rgb_para_hex(r, g, b),
            'cor_flutter': _converter_para_flutter(r, g, b, a),
        })

    # cor_para_flutter
    formato = dados.get('formato', 'hex')
    try:
        if formato == 'hex':
            valor = dados.get('valor', 'FF0000')
            a_val = 255
            tmp = valor.lstrip('#')
            if len(tmp) == 8:
                a_val = int(tmp[6:8], 16)
                tmp = tmp[:6]
            r, g, b, _ = _hex_para_rgb(tmp)
            a = a_val
        elif formato == 'rgb':
            r = max(0, min(255, int(dados.get('r', 0))))
            g = max(0, min(255, int(dados.get('g', 0))))
            b = max(0, min(255, int(dados.get('b', 0))))
            a = max(0, min(255, round(float(dados.get('a', 255)))))
        elif formato == 'hsl':
            h = float(dados.get('h', 0))
            s = float(dados.get('s', 0))
            l = float(dados.get('l', 0))
            r, g, b = _hsl_para_rgb(h, s, l)
            a = max(0, min(255, round(float(dados.get('a', 255)))))
        elif formato == 'hsv':
            h = float(dados.get('h', 0))
            s = float(dados.get('s', 0))
            v = float(dados.get('v', 0))
            r, g, b = _hsv_para_rgb(h, s, v)
            a = max(0, min(255, round(float(dados.get('a', 255)))))
        elif formato == 'cmyk':
            c = float(dados.get('c', 0))
            m = float(dados.get('m', 0))
            y = float(dados.get('y', 0))
            k = float(dados.get('k', 0))
            r, g, b = _cmyk_para_rgb(c, m, y, k)
            a = 255
        else:
            return jsonify({'erro': 'Formato nao suportado'}), 400

        return jsonify(_converter_para_flutter(r, g, b, a))
    except (ValueError, IndexError, TypeError):
        return jsonify({'erro': 'Valor de cor invalido'}), 400
