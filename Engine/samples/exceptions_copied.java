// Student B - Banking with error handling
// Java assignment

public class SafeAccount {

    private String id;
    private double funds;

    public SafeAccount(String id, double startFunds) {
        if (id == null || id.isEmpty()) {
            throw new IllegalArgumentException("Account ID cannot be empty");
        }
        if (startFunds < 0) {
            throw new IllegalArgumentException("Initial balance cannot be negative");
        }
        this.id = id;
        this.funds = startFunds;
    }

    public void addFunds(double amt) {
        if (amt <= 0) {
            throw new IllegalArgumentException("Deposit amount must be greater than zero");
        }
        funds += amt;
    }

    public void removeFunds(double amt) throws NotEnoughMoneyException {
        if (amt <= 0) {
            throw new IllegalArgumentException("Withdrawal amount must be greater than zero");
        }
        if (amt > funds) {
            throw new NotEnoughMoneyException(
                "Cannot withdraw " + amt + ", balance is only " + funds
            );
        }
        funds -= amt;
    }

    public double getFunds() {
        return funds;
    }

    public String getId() {
        return id;
    }

    public static class NotEnoughMoneyException extends Exception {
        private double deficit;

        public NotEnoughMoneyException(String msg) {
            super(msg);
        }

        public NotEnoughMoneyException(String msg, double deficit) {
            super(msg);
            this.deficit = deficit;
        }

        public double getDeficit() {
            return deficit;
        }
    }

    public static void main(String[] args) {
        try {
            SafeAccount acc = new SafeAccount("ACC001", 500.0);
            acc.addFunds(200.0);
            System.out.println("Balance after deposit: " + acc.getFunds());

            acc.removeFunds(100.0);
            System.out.println("Balance after withdrawal: " + acc.getFunds());

            acc.removeFunds(1000.0);

        } catch (IllegalArgumentException e) {
            System.out.println("Invalid input: " + e.getMessage());
        } catch (NotEnoughMoneyException e) {
            System.out.println("Error: " + e.getMessage());
        } finally {
            System.out.println("Transaction complete.");
        }

        try {
            SafeAccount bad = new SafeAccount("", 100.0);
        } catch (IllegalArgumentException e) {
            System.out.println("Caught: " + e.getMessage());
        }
    }
}
