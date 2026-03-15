// Switch Statement Example - Original
#include <iostream>
using namespace std;

string getDayName(int day) {
    string name;
    
    switch(day) {
        case 1:
            name = "Monday";
            break;
        case 2:
            name = "Tuesday";
            break;
        case 3:
            name = "Wednesday";
            break;
        case 4:
            name = "Thursday";
            break;
        case 5:
            name = "Friday";
            break;
        case 6:
            name = "Saturday";
            break;
        case 7:
            name = "Sunday";
            break;
        default:
            name = "Invalid day";
    }
    
    return name;
}

int main() {
    for(int i = 1; i <= 7; i++) {
        cout << "Day " << i << " is " << getDayName(i) << endl;
    }
    return 0;
}
