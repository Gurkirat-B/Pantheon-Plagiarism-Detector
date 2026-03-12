// Student L - Queue implementation using two stacks
// Completely different problem - should score very low vs everything else

#include <iostream>
#include <stack>
#include <stdexcept>

class QueueFromStacks {
private:
    std::stack<int> inbox;
    std::stack<int> outbox;

    void transfer() {
        if (outbox.empty()) {
            while (!inbox.empty()) {
                outbox.push(inbox.top());
                inbox.pop();
            }
        }
    }

public:
    void enqueue(int val) {
        inbox.push(val);
    }

    int dequeue() {
        transfer();
        if (outbox.empty())
            throw std::underflow_error("Queue is empty");
        int val = outbox.top();
        outbox.pop();
        return val;
    }

    int front() {
        transfer();
        if (outbox.empty())
            throw std::underflow_error("Queue is empty");
        return outbox.top();
    }

    bool isEmpty() {
        return inbox.empty() && outbox.empty();
    }

    int size() {
        return inbox.size() + outbox.size();
    }
};

int main() {
    QueueFromStacks q;
    q.enqueue(1);
    q.enqueue(2);
    q.enqueue(3);

    std::cout << "Front: " << q.front() << std::endl;
    std::cout << "Dequeue: " << q.dequeue() << std::endl;
    std::cout << "Dequeue: " << q.dequeue() << std::endl;

    q.enqueue(4);
    q.enqueue(5);

    std::cout << "Size: " << q.size() << std::endl;

    while (!q.isEmpty()) {
        std::cout << q.dequeue() << " ";
    }
    std::cout << std::endl;

    return 0;
}
