// Ternary Operator Example - Converted to If-Else
public class TernaryExample {
    
    public static String checkEvenOdd(int num) {
        if (num % 2 == 0) {
            return "Even";
        } else {
            return "Odd";
        }
    }
    
    public static int getMax(int a, int b) {
        if (a > b) {
            return a;
        } else {
            return b;
        }
    }
    
    public static String getGrade(int score) {
        if (score >= 90) {
            return "A";
        } else if (score >= 80) {
            return "B";
        } else if (score >= 70) {
            return "C";
        } else if (score >= 60) {
            return "D";
        } else {
            return "F";
        }
    }
    
    public static boolean isPositive(int x) {
        if (x > 0) {
            return true;
        } else {
            return false;
        }
    }
    
    public static String getStatus(int age) {
        if (age >= 18) {
            return "Adult";
        } else {
            return "Minor";
        }
    }
    
    public static void main(String[] args) {
        System.out.println("5 is: " + checkEvenOdd(5));
        System.out.println("10 is: " + checkEvenOdd(10));
        System.out.println("Max of 3 and 7: " + getMax(3, 7));
        System.out.println("Grade for 85: " + getGrade(85));
        System.out.println("Grade for 95: " + getGrade(95));
        System.out.println("25 is positive: " + isPositive(25));
        System.out.println("Status of 20: " + getStatus(20));
    }
}
