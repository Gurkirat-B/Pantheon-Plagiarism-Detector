// Student D - Generic container class
// Java Programming II

import java.util.ArrayList;
import java.util.EmptyStackException;

public class TypedStack<E> {

    private ArrayList<E> elements;
    private int limit;

    public TypedStack(int limit) {
        this.limit = limit;
        this.elements = new ArrayList<>();
    }

    public void push(E element) {
        if (elements.size() >= limit) {
            throw new StackOverflowError("Stack is full, max size: " + limit);
        }
        elements.add(element);
    }

    public E pop() {
        if (isEmpty()) {
            throw new EmptyStackException();
        }
        return elements.remove(elements.size() - 1);
    }

    public E peek() {
        if (isEmpty()) {
            throw new EmptyStackException();
        }
        return elements.get(elements.size() - 1);
    }

    public boolean isEmpty() {
        return elements.isEmpty();
    }

    public int size() {
        return elements.size();
    }

    public boolean contains(E element) {
        return elements.contains(element);
    }

    public void clear() {
        elements.clear();
    }

    @Override
    public String toString() {
        if (isEmpty()) return "[]";
        StringBuilder sb = new StringBuilder("[");
        for (int i = elements.size() - 1; i >= 0; i--) {
            sb.append(elements.get(i));
            if (i > 0) sb.append(", ");
        }
        sb.append("]");
        return sb.toString();
    }

    public static void main(String[] args) {
        TypedStack<Integer> intStack = new TypedStack<>(5);
        intStack.push(1);
        intStack.push(2);
        intStack.push(3);
        System.out.println("Int stack: " + intStack);
        System.out.println("Peek: " + intStack.peek());
        System.out.println("Pop: " + intStack.pop());
        System.out.println("After pop: " + intStack);

        TypedStack<String> strStack = new TypedStack<>(3);
        strStack.push("hello");
        strStack.push("world");
        System.out.println("String stack: " + strStack);
        System.out.println("Contains hello: " + strStack.contains("hello"));

        try {
            TypedStack<Integer> small = new TypedStack<>(2);
            small.push(1);
            small.push(2);
            small.push(3);
        } catch (StackOverflowError e) {
            System.out.println("Caught overflow: " + e.getMessage());
        }
    }
}
