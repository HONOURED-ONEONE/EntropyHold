fn only_digits(s: String) -> String:
    var result: String = ""
    for i in range(len(s)):
        let c = s[i]
        # ASCII check for digits
        if ord(c) >= 48 and ord(c) <= 57:
            result += c
    return result

fn format_indian_mobile(s: String) -> String:
    var d = only_digits(s)
    if d.startswith("91") and len(d) >= 12:
        return d[2:]
    if d.startswith("0") and len(d) >= 11:
        return d[1:]
    return d
