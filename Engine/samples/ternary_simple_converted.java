// Simple Ternary Example - Converted to If-Else
public class Utils {
    
    public int pickValue(boolean condition, int a, int b) {
        if (condition) {
            return a;
        } else {
            return b;
        }
    }
    
    public String checkSign(int num) {
        if (num > 0) {
            return "positive";
        } else if (num < 0) {
            return "negative";
        } else {
            return "zero";
        }
    }
    
    public int absolute(int val) {
        if (val < 0) {
            return -val;
        } else {
            return val;
        }
    }
    
    public boolean isAdult(int age) {
        if (age >= 18) {
            return true;
        } else {
            return false;
        }
    }
    
    public int min(int x, int y) {
        if (x < y) {
            return x;
        } else {
            return y;
        }
    }
    
    public int max(int x, int y) {
        if (x > y) {
            return x;
        } else {
            return y;
        }
    }
    
    public static void main(String[] args) {
        Utils u = new Utils();
        System.out.println(u.pickValue(true, 10, 20));
        System.out.println(u.checkSign(5));
        System.out.println(u.absolute(-15));
        System.out.println(u.isAdult(25));
        System.out.println(u.min(3, 7));
        System.out.println(u.max(3, 7));
    }
}
