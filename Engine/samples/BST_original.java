// Student C - BST Assignment
// Data Structures Fall 2024

public class BinarySearchTree {

    private class TreeNode {
        int key;
        TreeNode left, right;

        TreeNode(int key) {
            this.key = key;
            left = right = null;
        }
    }

    private TreeNode root;

    public BinarySearchTree() {
        root = null;
    }

    public void insert(int key) {
        root = insertRec(root, key);
    }

    private TreeNode insertRec(TreeNode node, int key) {
        if (node == null) {
            return new TreeNode(key);
        }
        if (key < node.key) {
            node.left = insertRec(node.left, key);
        } else if (key > node.key) {
            node.right = insertRec(node.right, key);
        }
        return node;
    }

    public boolean search(int key) {
        return searchRec(root, key);
    }

    private boolean searchRec(TreeNode node, int key) {
        if (node == null) return false;
        if (node.key == key) return true;
        if (key < node.key) return searchRec(node.left, key);
        return searchRec(node.right, key);
    }

    public void inorder() {
        inorderRec(root);
        System.out.println();
    }

    private void inorderRec(TreeNode node) {
        if (node != null) {
            inorderRec(node.left);
            System.out.print(node.key + " ");
            inorderRec(node.right);
        }
    }

    public int height() {
        return heightRec(root);
    }

    private int heightRec(TreeNode node) {
        if (node == null) return 0;
        int leftHeight  = heightRec(node.left);
        int rightHeight = heightRec(node.right);
        return 1 + Math.max(leftHeight, rightHeight);
    }

    public static void main(String[] args) {
        BinarySearchTree bst = new BinarySearchTree();
        int[] values = {50, 30, 70, 20, 40, 60, 80};
        for (int v : values) {
            bst.insert(v);
        }
        System.out.print("Inorder: ");
        bst.inorder();
        System.out.println("Height: " + bst.height());
        System.out.println("Search 40: " + bst.search(40));
        System.out.println("Search 99: " + bst.search(99));
    }
}
