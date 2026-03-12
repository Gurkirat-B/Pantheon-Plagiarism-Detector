// Student A - Exception handling assignment
// CSC 102 - Java Programming

public class BankAccountSafe {

    private String accountId;
    private double balance;

    public BankAccountSafe(String accountId, double initialBalance) {
        if (accountId == null || accountId.isEmpty()) {
            throw new IllegalArgumentException("Account ID cannot be empty");
        }
        if (initialBalance < 0) {
            throw new IllegalArgumentException("Initial balance cannot be negative");
        }
        this.accountId = accountId;
        this.balance = initialBalance;
    }

    public void deposit(double amount) {
        if (amount <= 0) {
            throw new IllegalArgumentException("Deposit amount must be greater than zero");
        }
        balance += amount;
    }

    public void withdraw(double amount) throws InsufficientFundsException {
        if (amount <= 0) {
            throw new IllegalArgumentException("Withdrawal amount must be greater than zero");
        }
        if (amount > balance) {
            throw new InsufficientFundsException(
                "Cannot withdraw " + amount + ", balance is only " + balance
            );
        }
        balance -= amount;
    }

    public double getBalance() {
        return balance;
    }

    public String getAccountId() {
        return accountId;
    }

    // custom exception class
    public static class InsufficientFundsException extends Exception {
        private double shortfall;

        public InsufficientFundsException(String message) {
            super(message);
        }

        public InsufficientFundsException(String message, double shortfall) {
            super(message);
            this.shortfall = shortfall;
        }

        public double getShortfall() {
            return shortfall;
        }
    }

    public static void main(String[] args) {
        try {
            BankAccountSafe acc = new BankAccountSafe("ACC001", 500.0);
            acc.deposit(200.0);
            System.out.println("Balance after deposit: " + acc.getBalance());

            acc.withdraw(100.0);
            System.out.println("Balance after withdrawal: " + acc.getBalance());

            // this should throw
            acc.withdraw(1000.0);

        } catch (InsufficientFundsException e) {
            System.out.println("Error: " + e.getMessage());
        } catch (IllegalArgumentException e) {
            System.out.println("Invalid input: " + e.getMessage());
        } finally {
            System.out.println("Transaction complete.");
        }

        // test invalid construction
        try {
            BankAccountSafe bad = new BankAccountSafe("", 100.0);
        } catch (IllegalArgumentException e) {
            System.out.println("Caught: " + e.getMessage());
        }
    }
}
