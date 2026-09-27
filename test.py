first_number = 564 
second_number = 563
first_number_result = 1
second_number_result = 1

for i in range(2, first_number + 1):
    first_number_result *= i

for b in range(2, second_number + 1):
    second_number_result *= b

print(first_number_result / second_number_result)
