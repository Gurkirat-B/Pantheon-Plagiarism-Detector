// Simple Ternary Example
public class Utils {
    
    public int pickValue(boolean condition, int a, int b) {
        return condition ? a : b;
    }
    
    public String checkSign(int num) {
        return (num > 0) ? "positive" : (num < 0) ? "negative" : "zero";
    }
    
    public int absolute(int val) {
        return (val < 0) ? -val : val;
    }
    
    public boolean isAdult(int age) {
        return (age >= 18) ? true : false;
    }
    
    public int min(int x, int y) {
        return (x < y) ? x : y;
    }
    
    public int max(int x, int y) {
        return (x > y) ? x : y;
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
