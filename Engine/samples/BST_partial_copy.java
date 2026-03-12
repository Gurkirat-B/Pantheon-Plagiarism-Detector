// Student K - BST with own insert logic but copied search/height from somewhere
// This is the partial copy scenario - containment score should catch this

public class TreeStructure {

    private class Node {
        int data;
        Node left, right;

        Node(int data) {
            this.data = data;
            this.left = null;
            this.right = null;
        }
    }

    private Node root;
    private int nodeCount;

    public TreeStructure() {
        root = null;
        nodeCount = 0;
    }

    // student wrote their own insert iteratively
    public void insert(int data) {
        Node newNode = new Node(data);
        if (root == null) {
            root = newNode;
            nodeCount++;
            return;
        }
        Node current = root;
        Node parent = null;
        while (current != null) {
            parent = current;
            if (data < current.data) {
                current = current.left;
            } else if (data > current.data) {
                current = current.right;
            } else {
                return; // duplicate
            }
        }
        if (data < parent.data) {
            parent.left = newNode;
        } else {
            parent.right = newNode;
        }
        nodeCount++;
    }

    // copied search from BST_original
    public boolean search(int key) {
        return searchRec(root, key);
    }

    private boolean searchRec(TreeNode node, int key) {
        if (node == null) return false;
        if (node.key == key) return true;
        if (key < node.key) return searchRec(node.left, key);
        return searchRec(node.right, key);
    }

    // copied height from BST_original
    public int height() {
        return heightRec(root);
    }

    private int heightRec(TreeNode node) {
        if (node == null) return 0;
        int leftHeight  = heightRec(node.left);
        int rightHeight = heightRec(node.right);
        return 1 + Math.max(leftHeight, rightHeight);
    }

    public void inorder() {
        printInorder(root);
        System.out.println();
    }

    private void printInorder(Node node) {
        if (node == null) return;
        printInorder(node.left);
        System.out.print(node.data + " ");
        printInorder(node.right);
    }

    public static void main(String[] args) {
        TreeStructure t = new TreeStructure();
        t.insert(15);
        t.insert(8);
        t.insert(22);
        t.insert(4);
        t.insert(11);
        t.inorder();
        System.out.println("Height: " + t.height());
        System.out.println("Has 8: " + t.search(8));
        System.out.println("Has 100: " + t.search(100));
    }
}
