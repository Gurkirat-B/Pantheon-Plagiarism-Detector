// Student E - Stack using array
// Written independently

public class Stack {

    private int[] arr;
    private int top;
    private int capacity;

    public Stack(int capacity) {
        this.capacity = capacity;
        arr = new int[capacity];
        top = -1;
    }

    public void push(int item) {
        if (isFull()) {
            System.out.println("Stack overflow");
            return;
        }
        arr[++top] = item;
    }

    public int pop() {
        if (isEmpty()) {
            System.out.println("Stack underflow");
            return -1;
        }
        return arr[top--];
    }

    public int peek() {
        if (isEmpty()) {
            System.out.println("Stack is empty");
            return -1;
        }
        return arr[top];
    }

    public boolean isEmpty() {
        return top == -1;
    }

    public boolean isFull() {
        return top == capacity - 1;
    }

    public int size() {
        return top + 1;
    }

    public void display() {
        if (isEmpty()) {
            System.out.println("Stack is empty");
            return;
        }
        System.out.print("Stack (top to bottom): ");
        for (int i = top; i >= 0; i--) {
            System.out.print(arr[i] + " ");
        }
        System.out.println();
    }

    public static void main(String[] args) {
        Stack s = new Stack(10);
        s.push(1);
        s.push(2);
        s.push(3);
        s.push(4);
        s.display();
        System.out.println("Peek: " + s.peek());
        System.out.println("Pop: " + s.pop());
        s.display();
        System.out.println("Size: " + s.size());
    }
}
