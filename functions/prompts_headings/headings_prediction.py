import numpy as np

def number_of_headings_to_be_extracted(x):
    #Hard coded coefficients and intercepts
    coefficients = np.array([[ 0.00000000e+00,  7.96028230e-01, -5.43853715e-02,
         2.02783198e-03, -4.47234814e-05,  5.74751738e-07,
        -3.89923860e-09,  1.06844198e-11]])
    intercept = np.array([3.20906638])

    y = intercept[0]
    
    # Add contribution from each coefficient
    for i, coef in enumerate(coefficients[0]):
        y += coef * (x**i)

    if(y>15): y=15   
    return round(y)

def expand(no_of_predicted_headings, no_of_required_headings, iteration=0):
    # Case when each page gets a summary
    if no_of_predicted_headings == no_of_required_headings:
        print(f"Iteration {iteration+1}")
        print([1] * no_of_predicted_headings)
        return [1] * no_of_predicted_headings

    summaries = []
    # Start by dividing pages into as many 2s as possible
    while no_of_predicted_headings >= 2:
        summaries.append(2)
        no_of_predicted_headings -= 2
    # Add remaining pages as 1s
    while no_of_predicted_headings > 0:
        summaries.append(1)
        no_of_predicted_headings -= 1

    # While the number of summaries obtained is less than required,
    # split the last '2' into two '1's.
    while len(summaries) < no_of_required_headings:
        if 2 in summaries:
            index_of_last_two = len(summaries) - 1 - summaries[::-1].index(2)  # find last occurrence of 2
            summaries.pop(index_of_last_two)  # remove the last 2
            summaries.extend([1, 1])  # add two 1s
        else:
            break  # no more 2s to split
    print(f"Iteration {iteration+1}")
    print(f"Page spans {summaries}")
    return summaries

def shrink(no_of_predicted_headings, no_of_required_headings):
    n = no_of_predicted_headings
    iteration = 1

    while True:
        print(f"Iteration {iteration}")
        summaries = []

        # Check if n is odd
        if n % 2 != 0:
            # Append (n-1)/2 number of 2s
            for _ in range((n - 1) // 2):
                summaries.append(2)
            summaries.append(1)  # for the last page
            n = len(summaries)  # update n for next iteration
        else:  # if n is even
            # Append n/2 number of 2s
            for _ in range(n // 2):
                summaries.append(2)
            n = len(summaries)  # update n for next iteration
        
        print(f"Page spans {summaries}")
        print("-----" * 5)

        # Breaking condition: Stop when n is less than or equal to no_of_required_summaries.
        if n <= no_of_required_headings*2:
            break

        iteration += 1

    return n, iteration

def predict_pagespan_headings(number_of_pages):
    number_of_headings = number_of_headings_to_be_extracted(number_of_pages)
    if number_of_pages==number_of_headings:
        expand(number_of_pages,number_of_headings)
    if number_of_pages>=(number_of_headings*2):
        if number_of_pages==(number_of_headings*2):
            shrink(number_of_pages, number_of_headings)
        else:
            n,iteration=shrink(number_of_pages, number_of_headings)
            expand(n,number_of_headings,iteration)
    if (number_of_pages<(number_of_headings*2))&(number_of_pages>number_of_headings):
        expand(number_of_pages, number_of_headings)
    if number_of_pages<number_of_headings:
        if number_of_pages==1:
            print([number_of_headings])
        else:
            expand(number_of_headings, number_of_pages)


