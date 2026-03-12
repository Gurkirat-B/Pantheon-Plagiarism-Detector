/* Student J - Hash Table from scratch
   Written independently, different approach entirely */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define TABLE_SIZE 100

typedef struct Entry {
    char key[50];
    int value;
    struct Entry* next;
} Entry;

typedef struct {
    Entry* buckets[TABLE_SIZE];
} HashTable;

unsigned int hash(const char* key) {
    unsigned int h = 0;
    while (*key) {
        h = (h * 31) + (unsigned char)(*key);
        key++;
    }
    return h % TABLE_SIZE;
}

HashTable* createTable() {
    HashTable* table = (HashTable*)malloc(sizeof(HashTable));
    int i;
    for (i = 0; i < TABLE_SIZE; i++) {
        table->buckets[i] = NULL;
    }
    return table;
}

void insert(HashTable* table, const char* key, int value) {
    unsigned int idx = hash(key);
    Entry* entry = table->buckets[idx];

    while (entry != NULL) {
        if (strcmp(entry->key, key) == 0) {
            entry->value = value;
            return;
        }
        entry = entry->next;
    }

    Entry* newEntry = (Entry*)malloc(sizeof(Entry));
    strncpy(newEntry->key, key, 49);
    newEntry->key[49] = '\0';
    newEntry->value = value;
    newEntry->next = table->buckets[idx];
    table->buckets[idx] = newEntry;
}

int get(HashTable* table, const char* key, int* found) {
    unsigned int idx = hash(key);
    Entry* entry = table->buckets[idx];
    while (entry != NULL) {
        if (strcmp(entry->key, key) == 0) {
            *found = 1;
            return entry->value;
        }
        entry = entry->next;
    }
    *found = 0;
    return 0;
}

void freeTable(HashTable* table) {
    int i;
    for (i = 0; i < TABLE_SIZE; i++) {
        Entry* entry = table->buckets[i];
        while (entry != NULL) {
            Entry* tmp = entry;
            entry = entry->next;
            free(tmp);
        }
    }
    free(table);
}

int main() {
    HashTable* table = createTable();
    insert(table, "apple", 5);
    insert(table, "banana", 12);
    insert(table, "cherry", 3);
    insert(table, "apple", 99);

    int found;
    int val = get(table, "apple", &found);
    if (found) printf("apple: %d\n", val);

    val = get(table, "banana", &found);
    if (found) printf("banana: %d\n", val);

    val = get(table, "mango", &found);
    if (!found) printf("mango: not found\n");

    freeTable(table);
    return 0;
}
