import re

def fix_latex(text: str) -> str:
    if not text:
        return ""

    # 1. Normalize line breaks around math delimiters
    # Convert \begin{equation}... \end{equation} or align to $$ ... $$
    text = re.sub(r'\\begin\{(?:equation|align|gather)\*?\}([\s\S]*?)\\end\{(?:equation|align|gather)\*?\}', r'$$\n\1\n$$', text)

    # 2. Convert explicit LaTeX display math \[ ... \] or \\[ ... \\] -> $$ ... $$
    text = re.sub(r'\\{1,2}\[([\s\S]*?)\\{1,2}\]', r'$$\n\1\n$$', text)

    # 3. Convert explicit LaTeX inline math \( ... \) or \\( ... \\) -> $ ... $
    text = re.sub(r'\\{1,2}\(([\s\S]*?)\\{1,2}\)', r'$\1$', text)

    # 4. Convert standalone brackets [ equation ] to $$ equation $$
    # Match [ content ] that is NOT a markdown link [text](url) and NOT a badge [BADGE]
    def bracket_to_display_math(match):
        full_match = match.group(0)
        content = match.group(1).strip()
        
        # If it's a badge like [TEACH], [DIRECT], [MATHEMATICS], [PHYSICS], [CHEMISTRY], [ORIENT], [PROBE], etc.
        if re.match(r'^[A-Z_/ ]+$', content) and len(content) <= 20:
            return full_match
            
        # Check for math indicators
        math_indicators = (
            '\\', '=', '+', '-', '*', '/', '^', '_', '<', '>',
            '\\frac', '\\dfrac', '\\text', '\\boxed', '\\Omega', '\\degree',
            '\\times', '\\cdot', '\\sqrt', '\\alpha', '\\beta', '\\theta',
            '\\mu', '\\rho', '\\pi', '\\Delta', '\\approx', '\\pm'
        )
        has_math = any(ind in content for ind in math_indicators)
        looks_like_eq = bool(re.search(r'[A-Za-z0-9_\{\}]+\s*=\s*[A-Za-z0-9_\{\}\\\s\.\,\+\-\*\/\(\)]+', content))
        
        if has_math or looks_like_eq:
            return f"\n$$\n{content}\n$$\n"
        return full_match

    text = re.sub(r'\[\s*([^\]\n]+?)\s*\](?!\()', bracket_to_display_math, text)

    # 5. Convert parenthesized LaTeX expressions into $ ... $
    def paren_to_inline_math(match):
        full_match = match.group(0)
        content = match.group(1).strip()
        math_indicators = (
            '\\text', '\\frac', '\\dfrac', '\\Omega', '\\qquad', '\\times',
            '\\cdot', '\\sqrt', '\\boxed', '\\alpha', '\\beta', '\\theta',
            '\\mu', '\\rho', '\\pi', '\\degree', '\\Delta', '_'
        )
        if any(ind in content for ind in math_indicators):
            return f"${content}$"
        return full_match

    text = re.sub(r'\(([^()\n]+?)\)', paren_to_inline_math, text)

    # 6. Ensure any standalone \boxed{...} not inside $ or $$ is wrapped in $$
    def boxed_fixer(match):
        prefix = match.group(1) # preceding char
        content = match.group(2)
        if prefix == '$':
            return match.group(0)
        return f"{prefix}$$\\boxed{{{content}}}$$"

    text = re.sub(r'(^|[^$])\\boxed\{([^{}]+)\}', boxed_fixer, text)

    # 7. Clean up any duplicated dollar signs or empty math blocks
    text = re.sub(r'\$\$\s*\$\$', '', text)
    
    return text


sample1 = r"""[MATHEMATICS] [DIRECT]
Identify the law to use – For a heater (or any resistive element) the relationship between potential difference (V), current (I) and resistance (R) is given by Ohm’s law

[ V = I R . ]

Find the resistance from the first situation

The heater has
[ V_1 = 60\ \text{V}, \qquad I_1 = 4\ \text{A}. ]

Rearranging Ohm’s law,

[ R = \frac{V_1}{I_1}= \frac{60\ \text{V}}{4\ \text{A}} = 15\ \Omega . ]

Use the same resistance for the second situation – The resistance of the heater does not change when the voltage is altered (the problem assumes a constant‑resistance heater).

Compute the new current when the voltage is doubled

New voltage: (V_2 = 120\ \text{V}).
Using (I = \dfrac{V}{R}),

[ I_2 = \frac{V_2}{R}= \frac{120\ \text{V}}{15\ \Omega}= 8\ \text{A}. ]

Check the result – Substitute (I_2) and (R) back into Ohm’s law:

[ V_{\text{check}} = I_2 R = 8\ \text{A}\times 15\ \Omega = 120\ \text{V}, ]

which matches the given voltage, confirming the calculation.

Answer:
[ \boxed{I = 8\ \text{A}} ]

If you’d like any step explained in more detail, just let me know!"""

result = fix_latex(sample1)
print("=== FIXED RESULT ===")
print(result)
