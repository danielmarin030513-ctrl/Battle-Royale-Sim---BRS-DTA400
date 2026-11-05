import random

class player:
    def __init__(self, name):
        self.name = name
        self.health = 150
        self.eliminations = 0
        self.weapon = snowball
        self.items = []
    def is_alive(self):
        return self.health > 0
    def attack(self, target):
        if random.random() <= self.weapon.accuracy:
            damage = self.weapon.roll_damage()
            target.health -= damage
            print(f"{self.name} attacked {target.name} with {self.weapon.name} for {damage} damage!")
        else:
            print(f"{self.name} missed the attack on {target.name}!")

class Items:
    def __init__(self, name, damage_min, damage_max, accuracy):
        self.name = name
        self.damage_min = damage_min
        self.damage_max = damage_max
        self.accuracy = accuracy
    def roll_damage(self):
        return random.randint(self.damage_min, self.damage_max)

snowball = Items("Snowball", 5, 10, 0.8)
ice_ball = Items("Ice Ball", 10, 20, 0.6)
snow_canon = Items("Snow Cannon", 15, 30, 0.4)

class HealthPack:
    def __init__(self, name, heal_amount):
        self.name = name
        self.heal_amount = heal_amount

hot_chocolate = HealthPack("Hot Chocolate", 30)
heat_pack = HealthPack("Heat Pack", 50)

