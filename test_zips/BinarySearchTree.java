public class BinarySearchTree {

    private static class Node {
        int key;
        Node left;
        Node right;

        Node(int k) {
            key = k;
            left = null;
            right = null;
        }
    }

    private Node root;

    public BinarySearchTree() {
        root = null;
    }

    public void insert(int key) {
        root = insertRec(root, key);
    }

    private Node insertRec(Node node, int key) {
        if (node == null) {
            return new Node(key);
        }
        if (key < node.key) {
            node.left = insertRec(node.left, key);
        } else if (key > node.key) {
            node.right = insertRec(node.right, key);
        }
        return node;
    }

    public boolean contains(int key) {
        return containsRec(root, key);
    }

    private boolean containsRec(Node node, int key) {
        if (node == null) {
            return false;
        }
        if (key == node.key) {
            return true;
        }
        if (key < node.key) {
            return containsRec(node.left, key);
        }
        return containsRec(node.right, key);
    }

    public void delete(int key) {
        root = deleteRec(root, key);
    }

    private Node deleteRec(Node node, int key) {
        if (node == null) {
            return null;
        }
        if (key < node.key) {
            node.left = deleteRec(node.left, key);
        } else if (key > node.key) {
            node.right = deleteRec(node.right, key);
        } else {
            if (node.left == null) {
                return node.right;
            }
            if (node.right == null) {
                return node.left;
            }
            int minVal = findMin(node.right);
            node.key = minVal;
            node.right = deleteRec(node.right, minVal);
        }
        return node;
    }

    private int findMin(Node node) {
        int min = node.key;
        while (node.left != null) {
            node = node.left;
            min = node.key;
        }
        return min;
    }

    public int height() {
        return heightRec(root);
    }

    private int heightRec(Node node) {
        if (node == null) {
            return 0;
        }
        int leftH = heightRec(node.left);
        int rightH = heightRec(node.right);
        if (leftH > rightH) {
            return leftH + 1;
        }
        return rightH + 1;
    }

    public int size() {
        return sizeRec(root);
    }

    private int sizeRec(Node node) {
        if (node == null) {
            return 0;
        }
        return 1 + sizeRec(node.left) + sizeRec(node.right);
    }

    public int[] toSortedArray() {
        int n = sizeRec(root);
        int[] arr = new int[n];
        int[] idx = {0};
        fillInorder(root, arr, idx);
        return arr;
    }

    private void fillInorder(Node node, int[] arr, int[] idx) {
        if (node == null) {
            return;
        }
        fillInorder(node.left, arr, idx);
        arr[idx[0]] = node.key;
        idx[0] = idx[0] + 1;
        fillInorder(node.right, arr, idx);
    }

    public boolean isBST() {
        return isBSTRec(root, Integer.MIN_VALUE, Integer.MAX_VALUE);
    }

    private boolean isBSTRec(Node node, int min, int max) {
        if (node == null) {
            return true;
        }
        if (node.key <= min || node.key >= max) {
            return false;
        }
        boolean leftOk = isBSTRec(node.left, min, node.key);
        boolean rightOk = isBSTRec(node.right, node.key, max);
        return leftOk && rightOk;
    }

    public int lowestCommonAncestor(int a, int b) {
        Node result = lcaRec(root, a, b);
        if (result == null) {
            return -1;
        }
        return result.key;
    }

    private Node lcaRec(Node node, int a, int b) {
        if (node == null) {
            return null;
        }
        if (a < node.key && b < node.key) {
            return lcaRec(node.left, a, b);
        }
        if (a > node.key && b > node.key) {
            return lcaRec(node.right, a, b);
        }
        return node;
    }

    public int kthSmallest(int k) {
        int[] count = {0};
        int[] result = {-1};
        kthRec(root, k, count, result);
        return result[0];
    }

    private void kthRec(Node node, int k, int[] count, int[] result) {
        if (node == null) {
            return;
        }
        kthRec(node.left, k, count, result);
        count[0] = count[0] + 1;
        if (count[0] == k) {
            result[0] = node.key;
            return;
        }
        kthRec(node.right, k, count, result);
    }

    public boolean isBalanced() {
        return balanceHeight(root) != -1;
    }

    private int balanceHeight(Node node) {
        if (node == null) {
            return 0;
        }
        int leftH = balanceHeight(node.left);
        if (leftH == -1) {
            return -1;
        }
        int rightH = balanceHeight(node.right);
        if (rightH == -1) {
            return -1;
        }
        int diff = leftH - rightH;
        if (diff > 1 || diff < -1) {
            return -1;
        }
        if (leftH > rightH) {
            return leftH + 1;
        }
        return rightH + 1;
    }

    public static void main(String[] args) {
        BinarySearchTree bst = new BinarySearchTree();
        int[] data = {50, 30, 70, 20, 40, 60, 80, 10, 25, 35, 45};
        for (int val : data) {
            bst.insert(val);
        }
        System.out.println("Height: " + bst.height());
        System.out.println("Size: " + bst.size());
        System.out.println("Contains 40: " + bst.contains(40));
        System.out.println("Contains 55: " + bst.contains(55));
        System.out.println("Valid BST: " + bst.isBST());
        System.out.println("Balanced: " + bst.isBalanced());
        System.out.println("LCA(20,45): " + bst.lowestCommonAncestor(20, 45));
        System.out.println("3rd smallest: " + bst.kthSmallest(3));
        bst.delete(30);
        System.out.println("After deleting 30:");
        System.out.println("Height: " + bst.height());
        System.out.println("Contains 30: " + bst.contains(30));
        int[] sorted = bst.toSortedArray();
        System.out.print("Sorted: ");
        for (int v : sorted) {
            System.out.print(v + " ");
        }
        System.out.println();
    }
}
