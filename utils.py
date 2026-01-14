def calculate_calories_goal(weight, height, age, active_minutes):
    return weight * 10 + height * 6.25 - age * 5 + 300 * (active_minutes // 30)


def calculate_water_goal(weight, active_minutes, temperature):
    extra_water = 0
    if temperature > 25:
        extra_water = 700
    return weight * 30 + 500 * (active_minutes // 30) + extra_water
