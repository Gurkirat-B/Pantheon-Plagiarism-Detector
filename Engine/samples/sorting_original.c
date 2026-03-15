/* Student F - Sorting Assignment
   CSC 102 - Algorithms */

#include <stdio.h>
#include <stdlib.h>

void bubbleSort(int arr[], int n) {
    int i, j, temp;
    for (i = 0; i < n - 1; i++) {
        for (j = 0; j < n - i - 1; j++) {
            if (arr[j] > arr[j + 1]) {
                temp = arr[j];
                arr[j] = arr[j + 1];
                arr[j + 1] = temp;
            }
        }
    }
}

void selectionSort(int arr[], int n) {
    int i, j, minIdx, temp;
    for (i = 0; i < n - 1; i++) {
        minIdx = i;
        for (j = i + 1; j < n; j++) {
            if (arr[j] < arr[minIdx]) {
                minIdx = j;
            }
        }
        temp = arr[minIdx];
        arr[minIdx] = arr[i];
        arr[i] = temp;
    }
}

void printArray(int arr[], int n) {
    int i;
    for (i = 0; i < n; i++) {
        printf("%d ", arr[i]);
    }
    printf("\n");
}

int binarySearch(int arr[], int n, int target) {
    int low = 0, high = n - 1, mid;
    while (low <= high) {
        mid = (low + high) / 2;
        if (arr[mid] == target) return mid;
        else if (arr[mid] < target) low = mid + 1;
        else high = mid - 1;
    }
    return -1;
}

int main() {
    int arr1[] = {64, 34, 25, 12, 22, 11, 90};
    int n = 7;

    printf("Original: ");
    printArray(arr1, n);

    bubbleSort(arr1, n);
    printf("Bubble sorted: ");
    printArray(arr1, n);

    int arr2[] = {64, 34, 25, 12, 22, 11, 90};
    selectionSort(arr2, n);
    printf("Selection sorted: ");
    printArray(arr2, n);

    int idx = binarySearch(arr1, n, 25);
    printf("Binary search for 25: index %d\n", idx);

    return 0;
}
