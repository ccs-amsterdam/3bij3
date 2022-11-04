testList = list(range(100))
print(testList)

testList = [ testList[i:i+10] for i in range(0, len(testList), 10)]

print("=====================================================")

print(testList)

for chunk in testList:
    print(chunk)
    print("--------")

# new_ids = [ new_ids[i:i+1000] for i in range(0, len(new_ids), 1000) ]
