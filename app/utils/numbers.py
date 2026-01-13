import re

def parse_money(value):
    """
    '250,00 TL 150,00 TL' -> (250.0, 150.0)
    '275,00 TL'           -> (275.0, None)
    """
    if not value:
        return None, None

    if isinstance(value, (int, float)):
        return float(value), None

    text = str(value)

    nums = re.findall(r"\d+[.,]\d+", text)
    nums = [float(n.replace(",", ".")) for n in nums]

    if len(nums) == 1:
        return nums[0], None
    elif len(nums) >= 2:
        return nums[0], nums[1]

    return None, None
