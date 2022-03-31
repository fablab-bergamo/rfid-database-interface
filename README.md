# rfid-access


## Roles
### Admin(s)
One or a few admins of the infrastructure
### Crew
The organization's Crew, performing specialistic maintenance, allowed to add new user
### User
A registered member of the organizzation.
#### User proprieties
- Membership number (like E000000)
- Anagraphic data
- Allowed machine types (filament 3D printers, resin 3D printers, lasers, CNC mills, other?)

## Endpoints

### Access endpoint
#### Purpose - general operation
This endpoint's purpose is to keep track of the presence of a user in the lab's facilities, in compliance to the COVID-19 regulations. At arrival, the user presents his card to the RFID reader and is then registered. When the user leaves, presents his card again to the reader and the exit time is registered. If no logout is made before 00AM, the user is automatically logged out, with 23:59:59 exit time. The access endpoint should show the number of active users on that moment.
#### Interface 
The user can interact with this endpoint via the RFID reader and a 16x2 LCD.
#### Checks:
- The presented card is associated to an existing user
- The existing user is on a current subscription (has not expired)
- The user is not yet logged in, if it is, logs out the user

### Machine endpoint
#### Purpose - general operation
This endpoint will be installed into the machines, cutting power to the machine, until a valid RFID card is presented. At this point starts the session for that user and powers up the machine. The session is then terminated by the user by presenting again the RFID card or by powering off the machine. **An user shouldn't be allowed to user any machine if didn't made access to the [access endpoint](#access-endpoint)**. 
#### Interface
The user can interact with this endpoint via the RFID reader and an RGB LED. Optionally, a 16x2 LCD can be added.
#### Statuses 
- Free: The user can start a new session presenting his card to the endpoint, the machine is turned on if that
- In use: 
- Maintenace required: After a fixed number of hours, the machine will require the user or the crew to do some checks or cleaning before starting operation
#### Checks:
- **ONLY IF** machine is in use: checks if the presented card belongs to the user using the machine. In this case logs off the user, otherwise rejects the user. 
- *Opt.*: The presented card is associated to an existing user
- *Opt.*: The existing user is on a valid subscription (has not expired)
- The user is logged in at the access endpoint 
- The user is authorized to use that machine type
- Some maintenance or periodic checks are not due

### Administrative endpoint
#### Purpose - general operation
The admin endpoint is a pc based application to which an admin has access. It might be a Python application (advantageous for the integration with the USB RFID reader) or a web browser page, or a combination of the two.

#### Capabilities
- **Crew**: Can register new users to the system and check their subscription's status
- **Crew**: Can renew a user subscription (yearly)
- **Crew**: Can enable a user for a specific machine type
- **Admin**: Can manage (add - remove - supsend for maintenace) machines
- **Admin**: Can show and export the users register for a certain date range
- **Admin**: Can show and export a certain machine's register for a certain date range

#### Checks:
- Requires admin or crew login (card + passoword or username + password: TBD)


## Server side
### Frontend

### Backend
