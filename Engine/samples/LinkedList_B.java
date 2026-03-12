// Student B - List implementation
// CSC 101

public class MyList {

    private class Element {
        int value;
        Element nextElement;

        Element(int value) {
            this.value = value;
            this.nextElement = null;
        }
    }

    private Element first;
    private int count;

    public MyList() {
        first = null;
        count = 0;
    }

    public void addToFront(int value) {
        Element elem = new Element(value);
        elem.nextElement = first;
        first = elem;
        count++;
    }

    public void addToEnd(int value) {
        Element elem = new Element(value);
        if (first == null) {
            first = elem;
        } else {
            Element curr = first;
            while (curr.nextElement != null) {
                curr = curr.nextElement;
            }
            curr.nextElement = elem;
        }
        count++;
    }

    public boolean remove(int value) {
        if (first == null) return false;

        if (first.value == value) {
            first = first.nextElement;
            count--;
            return true;
        }

        Element curr = first;
        while (curr.nextElement != null) {
            if (curr.nextElement.value == value) {
                curr.nextElement = curr.nextElement.nextElement;
                count--;
                return true;
            }
            curr = curr.nextElement;
        }
        return false;
    }

    public boolean find(int value) {
        Element curr = first;
        while (curr != null) {
            if (curr.value == value) return true;
            curr = curr.nextElement;
        }
        return false;
    }

    public void display() {
        Element curr = first;
        while (curr != null) {
            System.out.print(curr.value + " -> ");
            curr = curr.nextElement;
        }
        System.out.println("null");
    }

    public int length() {
        return count;
    }

    public static void main(String[] args) {
        MyList list = new MyList();
        list.addToEnd(10);
        list.addToEnd(20);
        list.addToEnd(30);
        list.addToFront(5);
        list.display();
        System.out.println("Size: " + list.length());
        list.remove(20);
        list.display();
        System.out.println("Search 10: " + list.find(10));
        System.out.println("Search 20: " + list.find(20));
    }
}
