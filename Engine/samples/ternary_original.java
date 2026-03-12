// Ternary Operator Example - Original
public class TernaryExample {
    
    public static String checkEvenOdd(int num) {
        return (num % 2 == 0) ? "Even" : "Odd";
    }
    
    public static int getMax(int a, int b) {
        return (a > b) ? a : b;
    }
    
    public static String getGrade(int score) {
        return (score >= 90) ? "A" : 
               (score >= 80) ? "B" : 
               (score >= 70) ? "C" : 
               (score >= 60) ? "D" : "F";
    }
    
    public static boolean isPositive(int x) {
        return (x > 0) ? true : false;
    }
    
    public static String getStatus(int age) {
        return (age >= 18) ? "Adult" : "Minor";
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
