bb = {2: 'two', 4: 'four', 6: 'six', 8: 'eight'}
aa = { i: i for i in range(10) if i in bb }

aa:dict[int, bool] = { i: False for i in range(10) }
aa[0].value = True
print(aa[0])