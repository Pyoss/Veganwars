import time
from multiprocessing.pool import ThreadPool
pool = ThreadPool(processes=1)



def test():
    time.sleep(5)
    return 5

async_result = pool.apply_async(test)
async_result_2 = pool.apply_async(test)
x = async_result.get()
y = async_result.get()
print(x)
print(y)