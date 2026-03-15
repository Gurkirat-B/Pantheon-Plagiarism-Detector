// Code Reordering Example - Completely Reordered
#include <stdio.h>
#include <stdlib.h>

int divideNumbers(int a, int b) {
    if (b == 0) return 0;
    return a / b;
}

int main() {
    int num1 = 20;
    int num2 = 5;
    
    printf("Add: %d\n", addNumbers(num1, num2));
    printf("Subtract: %d\n", subtractNumbers(num1, num2));
    printf("Multiply: %d\n", multiplyNumbers(num1, num2));
    printf("Divide: %d\n", divideNumbers(num1, num2));
    
    return 0;
}

int multiplyNumbers(int a, int b) {
    int result = a * b;
    return result;
}

int subtractNumbers(int a, int b) {
    int result = a - b;
    return result;
}

int addNumbers(int a, int b) {
    int result = a + b;
    return result;
}

