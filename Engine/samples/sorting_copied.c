/* Student G - Sorting homework
   Algorithms class */

#include <stdio.h>
#include <stdlib.h>

void bubSort(int data[], int len) {
    int x, y, tmp;
    for (x = 0; x < len - 1; x++) {
        for (y = 0; y < len - x - 1; y++) {
            if (data[y] > data[y + 1]) {
                tmp = data[y];
                data[y] = data[y + 1];
                data[y + 1] = tmp;
            }
        }
    }
}

void selSort(int data[], int len) {
    int x, y, minPos, tmp;
    for (x = 0; x < len - 1; x++) {
        minPos = x;
        for (y = x + 1; y < len; y++) {
            if (data[y] < data[minPos]) {
                minPos = y;
            }
        }
        tmp = data[minPos];
        data[minPos] = data[x];
        data[x] = tmp;
    }
}

void showArray(int data[], int len) {
    int x;
    for (x = 0; x < len; x++) {
        printf("%d ", data[x]);
    }
    printf("\n");
}

int binSearch(int data[], int len, int key) {
    int lo = 0, hi = len - 1, mid;
    while (lo <= hi) {
        mid = (lo + hi) / 2;
        if (data[mid] == key) return mid;
        else if (data[mid] < key) lo = mid + 1;
        else hi = mid - 1;
    }
    return -1;
}

int main() {
    int nums1[] = {64, 34, 25, 12, 22, 11, 90};
    int n = 7;

    printf("Original: ");
    showArray(nums1, n);

    bubSort(nums1, n);
    printf("Bubble sorted: ");
    showArray(nums1, n);

    int nums2[] = {64, 34, 25, 12, 22, 11, 90};
    selSort(nums2, n);
    printf("Selection sorted: ");
    showArray(nums2, n);

    int pos = binSearch(nums1, n, 25);
    printf("Binary search for 25: index %d\n", pos);

    return 0;
}
