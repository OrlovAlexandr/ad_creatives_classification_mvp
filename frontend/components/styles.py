def style_status(val):
    val_str = str(val)
    if val_str == "—":
        return "background-color: #ebebeb; color: #6c757d"
    elif val_str == "X":
        return "background-color: #f8d7da; color: #721c24"
    elif val_str.endswith("sec "):
        return "background-color: #fff3cd; color: #856404"
    elif val_str.endswith("sec"):
        return "background-color: #d4edda; color: #155724"
    return ""

def style_topic(val):
    return "font-weight: bold; font-size: 15px"
