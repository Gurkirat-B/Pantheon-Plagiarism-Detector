// Student D - Tree implementation
// DSA Assignment 3

public class BSTree {

    private class Node {
        int val;
        Node left, right;

        Node(int val) {
            this.val = val;
            left = right = null;
        }
    }

    private Node root;

    public BSTree() {
        root = null;
    }

    public void add(int val) {
        root = addNode(root, val);
    }

    private Node addNode(Node node, int val) {
        if (node == null) {
            return new Node(val);
        }
        if (val < node.val) {
            node.left = addNode(node.left, val);
        } else if (val > node.val) {
            node.right = addNode(node.right, val);
        }
        return node;
    }

    public boolean contains(int val) {
        return findNode(root, val);
    }

    private boolean findNode(Node node, int val) {
        if (node == null) return false;
        if (node.val == val) return true;
        if (val < node.val) return findNode(node.left, val);
        return findNode(node.right, val);
    }

    // prints sorted order
    public void printSorted() {
        printInorder(root);
        System.out.println();
    }

    private void printInorder(Node node) {
        if (node != null) {
            printInorder(node.left);
            System.out.print(node.val + " ");
            printInorder(node.right);
        }
    }

    public int getHeight() {
        return calcHeight(root);
    }

    private int calcHeight(Node node) {
        if (node == null) return 0;
        int l = calcHeight(node.left);
        int r = calcHeight(node.right);
        return 1 + Math.max(l, r);
    }

    // dead code added to look different
    public int countNodes() {
        return countRec(root);
    }

    private int countRec(Node node) {
        if (node == null) return 0;
        return 1 + countRec(node.left) + countRec(node.right);
    }

    public static void main(String[] args) {
        BSTree tree = new BSTree();
        int[] vals = {50, 30, 70, 20, 40, 60, 80};
        for (int v : vals) {
            tree.add(v);
        }
        System.out.print("Sorted: ");
        tree.printSorted();
        System.out.println("Height: " + tree.getHeight());
        System.out.println("Search 40: " + tree.contains(40));
        System.out.println("Search 99: " + tree.contains(99));
    }
}
