// Student C - Generic data structures
// Advanced Java assignment

import java.util.ArrayList;
import java.util.EmptyStackException;

public class GenericStack<T> {

    private ArrayList<T> items;
    private int maxSize;

    public GenericStack(int maxSize) {
        this.maxSize = maxSize;
        this.items = new ArrayList<>();
    }

    public void push(T item) {
        if (items.size() >= maxSize) {
            throw new StackOverflowError("Stack is full, max size: " + maxSize);
        }
        items.add(item);
    }

    public T pop() {
        if (isEmpty()) {
            throw new EmptyStackException();
        }
        return items.remove(items.size() - 1);
    }

    public T peek() {
        if (isEmpty()) {
            throw new EmptyStackException();
        }
        return items.get(items.size() - 1);
    }

    public boolean isEmpty() {
        return items.isEmpty();
    }

    public int size() {
        return items.size();
    }

    public boolean contains(T item) {
        return items.contains(item);
    }

    public void clear() {
        items.clear();
    }

    @Override
    public String toString() {
        if (isEmpty()) return "[]";
        StringBuilder sb = new StringBuilder("[");
        for (int i = items.size() - 1; i >= 0; i--) {
            sb.append(items.get(i));
            if (i > 0) sb.append(", ");
        }
        sb.append("]");
        return sb.toString();
    }

    public static void main(String[] args) {
        GenericStack<Integer> intStack = new GenericStack<>(5);
        intStack.push(1);
        intStack.push(2);
        intStack.push(3);
        System.out.println("Int stack: " + intStack);
        System.out.println("Peek: " + intStack.peek());
        System.out.println("Pop: " + intStack.pop());
        System.out.println("After pop: " + intStack);

        GenericStack<String> strStack = new GenericStack<>(3);
        strStack.push("hello");
        strStack.push("world");
        System.out.println("String stack: " + strStack);
        System.out.println("Contains hello: " + strStack.contains("hello"));

        try {
            GenericStack<Integer> small = new GenericStack<>(2);
            small.push(1);
            small.push(2);
            small.push(3); // should throw
        } catch (StackOverflowError e) {
            System.out.println("Caught overflow: " + e.getMessage());
        }
    }
}
