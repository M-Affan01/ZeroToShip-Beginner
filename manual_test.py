from models.component import Component

# Create a Component object
component = Component(1, "Arduino Uno", "Muhammad Affan")

print("Original Object:")
print(component)

# Convert object to dictionary
component_dict = component.to_dict()

print("\nDictionary:")
print(component_dict)

# Convert dictionary back to object
new_component = Component.from_dict(component_dict)

print("\nObject Created from Dictionary:")
print(new_component)